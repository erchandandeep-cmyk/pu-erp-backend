from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from accounts.models import User
from accounts.services import import_users_from_csv
from applications.models import Application, ApplicationType
from announcements.models import Announcement
from organizations.models import OrgUnit
from applications.services import suggest_authority
from audit.models import AuditLog
from .serializers import (
    LoginSerializer, UserSerializer, ApplicationSerializer,
    ApplicationTypeSerializer, AnnouncementSerializer, AuthoritySerializer
)

@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["username"].strip()
    password = serializer.validated_data["password"]
    user = User.objects.filter(employee_or_student_id__iexact=identifier).first()
    if not user:
        user = User.objects.filter(username__iexact=identifier).first()
    auth_user = authenticate(request, username=user.username if user else identifier, password=password)
    if not auth_user or not auth_user.is_active or not auth_user.is_active_account:
        return Response({"detail": "Invalid credentials or inactive account."}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=auth_user)
    return Response({"token": token.key, "user": UserSerializer(auth_user).data})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_api(request):
    return Response(UserSerializer(request.user).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def authorities_api(request):
    """
    Who the current user is allowed to address a new application to.

    Scoped to the applicant's own org unit (so the list stays short and
    relevant even with 300+ offices) PLUS anyone in a university-wide
    administrative office (Vice-Chancellor, Registrar, Deans, etc.) -
    those need to be reachable from any department, not just their own.
    """
    qs = User.objects.filter(
        role__in=[User.Role.TEACHER, User.Role.HOD, User.Role.STAFF, User.Role.ADMIN],
        is_active=True,
        is_active_account=True,
    )
    own_unit_id = getattr(request.user, "org_unit_id", None)
    admin_office_ids = OrgUnit.objects.filter(
        unit_type=OrgUnit.UnitType.ADMIN_OFFICE, is_active=True
    ).values_list("id", flat=True)

    if own_unit_id:
        qs = qs.filter(Q(org_unit_id=own_unit_id) | Q(org_unit_id__in=admin_office_ids))
    else:
        qs = qs.filter(org_unit_id__in=admin_office_ids)

    qs = qs.order_by("first_name", "last_name")
    return Response(AuthoritySerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def suggest_authority_api(request):
    """
    Given ?application_type=<id>, returns who this should default to
    based on that type's configurable routing rule (see
    applications.services.suggest_authority) - or {"authority": null}
    if nobody matches, in which case the caller should let the person
    pick manually from the full list instead.
    """
    type_id = request.query_params.get("application_type")
    if not type_id:
        return Response({"detail": "application_type is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        app_type = ApplicationType.objects.get(pk=type_id, active=True)
    except ApplicationType.DoesNotExist:
        return Response({"detail": "Unknown or inactive application type."}, status=status.HTTP_404_NOT_FOUND)

    match = suggest_authority(request.user, app_type)
    if match is None:
        return Response({"authority": None})
    return Response({"authority": AuthoritySerializer(match).data})


class ApplicationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationType.objects.filter(active=True).order_by("name")
    serializer_class = ApplicationTypeSerializer
    permission_classes = [IsAuthenticated]

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Application.objects.select_related(
            "application_type", "applicant", "authority"
        ).order_by("-created_at")

        if user.is_superuser or user.role == User.Role.ADMIN:
            # Admins/superusers can see everything - needed for
            # university-wide oversight (e.g. Registrar's office).
            base = qs
        elif user.role == User.Role.STUDENT:
            base = qs.filter(applicant=user)
        else:
            # Teacher / Staff / HOD: their own submitted applications,
            # plus anything currently sitting with them to act on.
            # (Previously this returned Application.objects.all() -
            # every application in the entire university, regardless of
            # department. That was a real privacy bug, fixed here.)
            base = qs.filter(Q(applicant=user) | Q(authority=user))

        if self.request.query_params.get("inbox") == "true":
            base = base.filter(authority=user)

        return base

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.STUDENT:
            return Response({"detail": "Only students can submit new applications."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        obj = serializer.save(applicant=self.request.user)
        AuditLog.objects.create(
            actor=self.request.user,
            action="APPLICATION_SUBMITTED",
            object_type="Application",
            object_id=str(obj.pk),
            details=f"{obj.application_id} (via mobile app)",
        )

    def update(self, request, *args, **kwargs):
        if request.user.role not in {User.Role.TEACHER, User.Role.STAFF, User.Role.HOD, User.Role.ADMIN} and not request.user.is_superuser:
            return Response({"detail": "You do not have permission to process applications."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        if request.user.role not in {User.Role.TEACHER, User.Role.STAFF, User.Role.HOD, User.Role.ADMIN} and not request.user.is_superuser:
            return Response({"detail": "You do not have permission to process applications."}, status=status.HTTP_403_FORBIDDEN)
        application = self.get_object()
        action_name = str(request.data.get("action", "")).upper()
        remark = str(request.data.get("remark", "")).strip()
        status_map = {
            "APPROVE": Application.Status.APPROVED,
            "REJECT": Application.Status.REJECTED,
            "REVIEW": Application.Status.UNDER_REVIEW,
            "FORWARD": Application.Status.FORWARDED,
            "COMPLETE": Application.Status.COMPLETED,
        }
        if action_name not in status_map:
            return Response({"detail": "Invalid action. Use APPROVE, REJECT, REVIEW, FORWARD or COMPLETE."}, status=status.HTTP_400_BAD_REQUEST)

        history_note = remark

        if action_name == "FORWARD":
            forward_user_id = request.data.get("forward_user")
            if not forward_user_id:
                return Response({"detail": "forward_user is required to forward an application."}, status=status.HTTP_400_BAD_REQUEST)

            allowed_forward_roles = {
                "TEACHER": {"STAFF", "HOD", "ADMIN"},
                "STAFF": {"HOD", "ADMIN"},
                "HOD": {"TEACHER", "STAFF", "HOD", "ADMIN"},
                "ADMIN": {"TEACHER", "STAFF", "HOD", "ADMIN"},
            }
            allowed_roles = allowed_forward_roles.get(request.user.role, set()) if not request.user.is_superuser else set(status_map) | {"TEACHER", "STAFF", "HOD", "ADMIN"}

            try:
                target_user = User.objects.get(pk=forward_user_id, is_active=True, is_active_account=True)
            except User.DoesNotExist:
                return Response({"detail": "The selected recipient was not found or is inactive."}, status=status.HTTP_400_BAD_REQUEST)

            if target_user.role not in allowed_roles and not request.user.is_superuser:
                return Response({"detail": f"You are not allowed to forward to a {target_user.get_role_display()}."}, status=status.HTTP_403_FORBIDDEN)

            if target_user.pk == request.user.pk:
                return Response({"detail": "You cannot forward an application to yourself."}, status=status.HTTP_400_BAD_REQUEST)

            application.authority = target_user
            target_name = target_user.get_full_name() or target_user.username
            history_note = remark or f"Application forwarded to {target_name}."

        application.status = status_map[action_name]
        application.current_remark = remark
        update_fields = ["status", "current_remark", "updated_at"]
        if action_name == "FORWARD":
            update_fields.append("authority")
        application.save(update_fields=update_fields)
        from applications.models import ApplicationHistory
        from notifications.models import Notification
        ApplicationHistory.objects.create(application=application, actor=request.user, action=action_name.title(), remark=history_note)
        AuditLog.objects.create(
            actor=request.user,
            action=f"APPLICATION_{action_name}",
            object_type="Application",
            object_id=str(application.pk),
            details=f"{application.application_id}: {history_note} (via mobile app)",
        )
        Notification.objects.create(user=application.applicant, title=f"Application {action_name.lower()}", message=f"{application.application_id} is now {application.get_status_display()}. {remark}".strip(), link=f"/applications/{application.pk}/")
        if action_name == "FORWARD":
            Notification.objects.create(user=application.authority, title="Application forwarded to you", message=f"{application.application_id}: {application.subject}", link=f"/applications/{application.pk}/")
        return Response(ApplicationSerializer(application).data)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Applications cannot be deleted."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        role_to_audience = {
            User.Role.STUDENT: ["ALL", "STUDENTS"],
            User.Role.TEACHER: ["ALL", "TEACHERS"],
            User.Role.STAFF: ["ALL", "STAFF"],
            User.Role.HOD: ["ALL", "HOD"],
            User.Role.ADMIN: ["ALL"],
        }
        return Announcement.objects.filter(active=True, audience__in=role_to_audience.get(self.request.user.role, ["ALL"])).order_by("-published_at")

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_users_api(request):
    if request.user.role not in {User.Role.STAFF, User.Role.HOD, User.Role.ADMIN} and not request.user.is_superuser:
        return Response({"detail": "Only departmental office staff, HOD or admin can import users."}, status=status.HTTP_403_FORBIDDEN)
    uploaded = request.FILES.get("file")
    if not uploaded:
        return Response({"detail": "Upload a CSV file using the 'file' field."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = import_users_from_csv(uploaded, request.user)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)
