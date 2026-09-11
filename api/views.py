from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from accounts.models import User
from accounts.services import import_users_from_csv
from applications.models import Application, ApplicationType
from announcements.models import Announcement
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
    Scoped to the applicant's own org unit once one is set, so this stays
    a short, relevant list even after the university has 300+ offices.
    """
    qs = User.objects.filter(
        role__in=[User.Role.TEACHER, User.Role.HOD, User.Role.STAFF, User.Role.ADMIN],
        is_active=True,
        is_active_account=True,
    )
    if getattr(request.user, "org_unit_id", None):
        qs = qs.filter(org_unit_id=request.user.org_unit_id)
    qs = qs.order_by("first_name", "last_name")
    return Response(AuthoritySerializer(qs, many=True).data)


class ApplicationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationType.objects.filter(active=True).order_by("name")
    serializer_class = ApplicationTypeSerializer
    permission_classes = [IsAuthenticated]

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return Application.objects.filter(applicant=user).select_related("application_type", "applicant").order_by("-created_at")
        return Application.objects.all().select_related("application_type", "applicant").order_by("-created_at")

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.STUDENT:
            return Response({"detail": "Only students can submit new applications."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

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
        application.status = status_map[action_name]
        application.current_remark = remark
        application.save(update_fields=["status", "current_remark", "updated_at"])
        from applications.models import ApplicationHistory
        from notifications.models import Notification
        ApplicationHistory.objects.create(application=application, actor=request.user, action=action_name.title(), remark=remark)
        Notification.objects.create(user=application.applicant, title=f"Application {action_name.lower()}", message=f"{application.application_id} is now {application.get_status_display()}. {remark}".strip(), link=f"/applications/{application.pk}/")
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
