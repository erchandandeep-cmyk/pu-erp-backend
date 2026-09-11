from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ImproperlyConfigured
from .forms import ApplicationForm
from .models import (
    Application,
    ApplicationHistory,
    ApplicationType,
)

from notifications.models import Notification


def _render_pdf(html_string, base_url):
    """
    PDF export needs the WeasyPrint library, which in turn needs a
    system library (GTK3, specifically Pango/cairo/gobject) that is
    NOT installed by pip - it must be installed separately at the OS
    level. Importing weasyprint is deferred to here (instead of at
    the top of this file) so that a missing GTK3 install only breaks
    the "Download PDF" button, not the entire application (migrate,
    admin, login, everything else keeps working normally).

    To enable PDF export on Windows: install the GTK3 runtime from
    https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
    then restart your terminal (close and reopen cmd) and try again.
    """
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise ImproperlyConfigured(
            "PDF export needs the GTK3 runtime library, which isn't "
            "installed on this machine yet. Install it from "
            "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases "
            "then restart your terminal and try again. "
            f"(underlying error: {exc})"
        )
    return HTML(string=html_string, base_url=base_url).write_pdf()
from audit.models import AuditLog


# =========================================================
# USERS WHO CAN PROCESS APPLICATIONS
# =========================================================

def can_process(user):
    """
    Users who are allowed to process applications.
    """

    return (
        user.is_superuser
        or user.role in {"TEACHER", "STAFF", "HOD", "ADMIN"}
    )


# =========================================================
# GET USER MODEL
# =========================================================

def user_model():
    """
    Get the project's configured User model.
    """

    from django.contrib.auth import get_user_model

    return get_user_model()


# =========================================================
# GET USERS BY ROLE
# =========================================================

def get_users_by_role(role):
    """
    Return active users having the requested role.
    """

    User = user_model()

    return (
        User.objects.filter(
            role=role,
            is_active=True,
            is_active_account=True,
        )
        .order_by("first_name", "last_name")
    )


# =========================================================
# APPLICATION LIST
# =========================================================


@login_required
def application_list(request):

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    q = request.GET.get("q", "").strip()

    # ---------------------------------------------------------
    # FILTERS
    # ---------------------------------------------------------

    status = request.GET.get("status", "").strip()

    application_type = request.GET.get(
        "application_type",
        ""
    ).strip()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    # ---------------------------------------------------------
    # PROCESSING USERS
    # ---------------------------------------------------------

    if can_process(request.user):

        qs = Application.objects.filter(
            is_archived=False
        )

    # ---------------------------------------------------------
    # NORMAL STUDENT
    # ---------------------------------------------------------

    else:

     qs = Application.objects.filter(
        applicant=request.user
     )

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    if q:

        qs = qs.filter(
            Q(
                application_id__icontains=q
            )
            |
            Q(
                subject__icontains=q
            )
            |
            Q(
                applicant__first_name__icontains=q
            )
            |
            Q(
                applicant__last_name__icontains=q
            )
            |
            Q(
                applicant__username__icontains=q
            )
        )

    # ---------------------------------------------------------
    # STATUS FILTER
    # ---------------------------------------------------------

    if status:

        qs = qs.filter(
            status=status
        )

    # ---------------------------------------------------------
    # APPLICATION TYPE FILTER
    # ---------------------------------------------------------

    if application_type:

        qs = qs.filter(
            application_type_id=application_type
        )

    # ---------------------------------------------------------
    # DATE FROM
    # ---------------------------------------------------------

    if date_from:

        qs = qs.filter(
            created_at__date__gte=date_from
        )

    # ---------------------------------------------------------
    # DATE TO
    # ---------------------------------------------------------

    if date_to:

        qs = qs.filter(
            created_at__date__lte=date_to
        )

    # ---------------------------------------------------------
    # APPLICATION TYPES
    # ---------------------------------------------------------

    application_types = ApplicationType.objects.filter(
        active=True
    ).order_by("name")

    # ---------------------------------------------------------
    # FINAL QUERY
    # ---------------------------------------------------------

    applications = qs.select_related(
        "applicant",
        "application_type",
        "authority",
    ).order_by(
        "-created_at"
    )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "applications/list.html",
        {
            "applications": applications,

            # Search
            "q": q,

            # Filters
            "status": status,
            "application_type": application_type,
            "date_from": date_from,
            "date_to": date_to,

            # Choices
            "status_choices": Application.Status.choices,
            "application_types": application_types,
        },
    )


# =========================================================
# CREATE APPLICATION
# =========================================================

@login_required
def create_application(request):

    form = ApplicationForm(
        request.POST or None,
        request.FILES or None,
        applicant=request.user,
    )

    if request.method == "POST" and form.is_valid():

        obj = form.save(commit=False)

        # -----------------------------------------------------
        # STUDENT WHO SUBMITTED THE APPLICATION
        # -----------------------------------------------------

        obj.applicant = request.user

        obj.status = Application.Status.SUBMITTED

        obj.save()

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        ApplicationHistory.objects.create(
            application=obj,
            actor=request.user,
            action="Submitted",
            remark="Application submitted.",
        )

        # -----------------------------------------------------
        # NOTIFY INITIAL AUTHORITY
        # -----------------------------------------------------

        if obj.authority:

            Notification.objects.create(
                user=obj.authority,
                title="New application received",
                message=(
                    f"{obj.application_id}: "
                    f"{obj.subject}"
                ),
                link=f"/applications/{obj.pk}/",
            )

        # -----------------------------------------------------
        # AUDIT LOG
        # -----------------------------------------------------

        AuditLog.objects.create(
            actor=request.user,
            action="APPLICATION_SUBMITTED",
            object_type="Application",
            object_id=str(obj.pk),
            details=obj.application_id,
        )

        messages.success(
            request,
            (
                "Application submitted successfully. "
                f"ID: {obj.application_id}"
            ),
        )

        return redirect(
            "application_detail",
            pk=obj.pk
        )

    return render(
        request,
        "applications/form.html",
        {
            "form": form
        }
    )


# =========================================================
# APPLICATION DETAIL
# =========================================================
@login_required
def application_detail(request, pk):

    obj = get_object_or_404(
        Application.objects.select_related(
            "applicant",
            "authority",
            "application_type",
        ),
        pk=pk,
    )

    # ---------------------------------------------------------
    # PERMISSION
    # ---------------------------------------------------------

    if (
        request.user != obj.applicant
        and not can_process(request.user)
    ):
        raise PermissionDenied

    # ---------------------------------------------------------
    # APPLICATION HISTORY / TIMELINE
    # ---------------------------------------------------------

    history = (
        ApplicationHistory.objects.filter(
            application=obj
        )
        .select_related("actor")
        .order_by("created_at")
    )

    # ---------------------------------------------------------
    # FORWARDING OPTIONS
    # ---------------------------------------------------------

    forward_teacher = []
    forward_staff = []
    forward_hod = []

    # =========================================================
    # TEACHER
    # =========================================================

    if request.user.role == "TEACHER":

        # Teacher -> Staff / HOD
        forward_staff = get_users_by_role("STAFF")
        forward_hod = get_users_by_role("HOD")

    # =========================================================
    # STAFF
    # =========================================================

    elif request.user.role == "STAFF":

        # Staff -> HOD
        forward_hod = get_users_by_role("HOD")

    # =========================================================
    # HOD
    # =========================================================

    elif request.user.role == "HOD":

        # HOD -> Teacher / Staff / HOD
        forward_teacher = get_users_by_role("TEACHER")
        forward_staff = get_users_by_role("STAFF")
        forward_hod = get_users_by_role("HOD")

    # =========================================================
    # ADMIN
    # =========================================================

    elif request.user.role == "ADMIN" or request.user.is_superuser:

        # Admin -> Teacher / Staff / HOD
        forward_teacher = get_users_by_role("TEACHER")
        forward_staff = get_users_by_role("STAFF")
        forward_hod = get_users_by_role("HOD")

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "applications/detail.html",
        {
            "application": obj,

            # Application timeline
            "history": history,

            # Forwarding options
            "forward_teacher": forward_teacher,
            "forward_staff": forward_staff,
            "forward_hod": forward_hod,
        },
    )
# =========================================================
# APPLICATION PDF
# =========================================================

@login_required
def application_pdf(request, pk):

    obj = get_object_or_404(
        Application.objects.select_related(
            "applicant",
            "authority",
            "application_type",
        ),
        pk=pk,
    )

    # ---------------------------------------------------------
    # PERMISSION
    # ---------------------------------------------------------

    if (
        request.user != obj.applicant
        and not can_process(request.user)
    ):
        raise PermissionDenied

    # ---------------------------------------------------------
    # APPLICATION HISTORY
    # ---------------------------------------------------------

    history = (
        ApplicationHistory.objects.filter(
            application=obj
        )
        .select_related("actor")
        .order_by("created_at")
    )

    # ---------------------------------------------------------
    # PDF HTML
    # ---------------------------------------------------------

    html_string = render(
        request,
        "applications/application_pdf.html",
        {
            "application": obj,
            "history": history,
        },
    ).content.decode("utf-8")

    # ---------------------------------------------------------
    # GENERATE PDF
    # ---------------------------------------------------------

    pdf = _render_pdf(html_string, request.build_absolute_uri("/"))

    # ---------------------------------------------------------
    # RESPONSE
    # ---------------------------------------------------------

    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'inline; filename="{obj.application_id}.pdf"'
    )

    return response
# =========================================================
# APPLICATION ACTION
# =========================================================

@login_required
def application_action(request, pk, action):

    # ---------------------------------------------------------
    # ONLY AUTHORIZED USERS CAN PROCESS
    # ---------------------------------------------------------

    if not can_process(request.user):

        raise PermissionDenied

    obj = get_object_or_404(
        Application,
        pk=pk
    )

    # ---------------------------------------------------------
    # ONLY POST REQUESTS
    # ---------------------------------------------------------

    if request.method != "POST":

        return redirect(
            "application_detail",
            pk=pk
        )

    # ---------------------------------------------------------
    # REMARK
    # ---------------------------------------------------------

    remark = request.POST.get(
        "remark",
        ""
    ).strip()

    # =========================================================
    # FORWARD APPLICATION
    # =========================================================

    if action == "forward":

        # -----------------------------------------------------
        # DESTINATION ROLE
        # -----------------------------------------------------

        forward_to = request.POST.get(
            "forward_to",
            ""
        ).strip().upper()

        # -----------------------------------------------------
        # SELECTED USER
        # -----------------------------------------------------

        selected_user_id = request.POST.get(
            "forward_user",
            ""
        ).strip()

        # -----------------------------------------------------
        # VALID FORWARDING RULES
        # -----------------------------------------------------

        allowed_forward_roles = {
            "TEACHER": {"STAFF", "HOD"},
            "STAFF": {"HOD"},
            "HOD": {"TEACHER", "STAFF", "HOD"},
            "ADMIN": {"TEACHER", "STAFF", "HOD"},
        }

        allowed_roles = allowed_forward_roles.get(
            request.user.role,
            set()
        )

        # -----------------------------------------------------
        # CHECK DESTINATION ROLE
        # -----------------------------------------------------

        if forward_to not in allowed_roles:

            messages.error(
                request,
                "You are not allowed to forward an application "
                f"to {forward_to.title() if forward_to else 'this role'}."
            )

            return redirect(
                "application_detail",
                pk=pk
            )

        # -----------------------------------------------------
        # CHECK PERSON
        # -----------------------------------------------------

        if not selected_user_id:

            messages.error(
                request,
                "Please select the person to whom "
                "the application should be forwarded."
            )

            return redirect(
                "application_detail",
                pk=pk
            )

        # -----------------------------------------------------
        # GET SELECTED USER
        # -----------------------------------------------------

        User = user_model()

        target_user = get_object_or_404(
            User,
            pk=selected_user_id,
            role=forward_to,
            is_active=True,
            is_active_account=True,
        )

        # -----------------------------------------------------
        # PREVENT FORWARDING TO SELF
        # -----------------------------------------------------

        if target_user.pk == request.user.pk:

            messages.error(
                request,
                "You cannot forward an application to yourself."
            )

            return redirect(
                "application_detail",
                pk=pk
            )

        # -----------------------------------------------------
        # ASSIGN NEW AUTHORITY
        # -----------------------------------------------------

        obj.authority = target_user

        obj.status = Application.Status.FORWARDED

        obj.current_remark = remark

        obj.save(
            update_fields=[
                "authority",
                "status",
                "current_remark",
                "updated_at",
            ]
        )

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        target_name = (
            target_user.get_full_name()
            or target_user.username
        )

        ApplicationHistory.objects.create(
            application=obj,
            actor=request.user,
            action=(
                f"Forwarded to "
                f"{target_user.get_role_display()}"
            ),
            remark=(
                remark
                or
                (
                    "Application forwarded to "
                    f"{target_name}."
                )
            ),
        )

        # -----------------------------------------------------
        # NOTIFY NEW AUTHORITY
        # -----------------------------------------------------

        Notification.objects.create(
            user=target_user,
            title="Application forwarded to you",
            message=(
                f"{obj.application_id}: "
                f"{obj.subject}"
            ),
            link=f"/applications/{obj.pk}/",
        )

        # -----------------------------------------------------
        # NOTIFY STUDENT
        # -----------------------------------------------------

        Notification.objects.create(
            user=obj.applicant,
            title="Application forwarded",
            message=(
                f"{obj.application_id} has been "
                f"forwarded to "
                f"{target_user.get_role_display()} "
                f"({target_name})."
            ),
            link=f"/applications/{obj.pk}/",
        )

        # -----------------------------------------------------
        # AUDIT
        # -----------------------------------------------------

        AuditLog.objects.create(
            actor=request.user,
            action="APPLICATION_FORWARDED",
            object_type="Application",
            object_id=str(obj.pk),
            details=(
                f"Forwarded to "
                f"{target_user.username}. "
                f"{remark}"
            ),
        )

        # -----------------------------------------------------
        # SUCCESS MESSAGE
        # -----------------------------------------------------

        messages.success(
            request,
            (
                "Application successfully forwarded to "
                f"{target_name}."
            ),
        )

        return redirect(
            "application_detail",
            pk=pk
        )

    # =========================================================
    # ARCHIVE APPLICATION
    # =========================================================

    if action == "archive":

        # -----------------------------------------------------
        # ONLY HOD OR ADMIN CAN ARCHIVE
        # -----------------------------------------------------

        if request.user.role not in {
            "HOD",
            "ADMIN",
        }:

            raise PermissionDenied

        # -----------------------------------------------------
        # ONLY APPROVED OR REJECTED APPLICATIONS
        # CAN BE ARCHIVED
        # -----------------------------------------------------

        if obj.status not in {
            Application.Status.APPROVED,
            Application.Status.REJECTED,
        }:

            messages.error(
                request,
                "Only approved or rejected applications "
                "can be archived."
            )

            return redirect(
                "application_detail",
                pk=pk
            )

        # -----------------------------------------------------
        # CHECK IF ALREADY ARCHIVED
        # -----------------------------------------------------

        if obj.is_archived:

            messages.info(
                request,
                "This application is already archived."
            )

            return redirect(
                "application_detail",
                pk=pk
            )

        # -----------------------------------------------------
        # ARCHIVE APPLICATION
        # -----------------------------------------------------

        obj.is_archived = True

        obj.save(
            update_fields=[
                "is_archived"
            ]
        )

        # -----------------------------------------------------
        # WORKFLOW HISTORY
        # -----------------------------------------------------

        ApplicationHistory.objects.create(
            application=obj,
            actor=request.user,
            action="Application Archived",
            remark=(
                remark
                or
                "Application archived by HOD/Admin."
            ),
        )

        # -----------------------------------------------------
        # AUDIT LOG
        # -----------------------------------------------------

        AuditLog.objects.create(
            actor=request.user,
            action="APPLICATION_ARCHIVED",
            object_type="Application",
            object_id=str(obj.pk),
            details=(
                remark
                or
                "Application archived."
            ),
        )

        # -----------------------------------------------------
        # NOTIFY STUDENT
        # -----------------------------------------------------

        Notification.objects.create(
            user=obj.applicant,
            title="Application Archived",
            message=(
                f"{obj.application_id} has been archived."
            ),
            link=f"/applications/{obj.pk}/",
        )

        # -----------------------------------------------------
        # SUCCESS MESSAGE
        # -----------------------------------------------------

        messages.success(
            request,
            "Application archived successfully."
        )

        return redirect(
            "application_list"
        )

    # =========================================================
    # OTHER APPLICATION ACTIONS
    # =========================================================

    action_map = {

        "approve": (
            Application.Status.APPROVED,
            "Approved",
        ),

        "reject": (
            Application.Status.REJECTED,
            "Rejected",
        ),

        "review": (
            Application.Status.UNDER_REVIEW,
            "Marked under review",
        ),

        "complete": (
            Application.Status.COMPLETED,
            "Completed",
        ),
    }

    # ---------------------------------------------------------
    # INVALID ACTION
    # ---------------------------------------------------------

    if action not in action_map:

        raise PermissionDenied

    # ---------------------------------------------------------
    # GET STATUS
    # ---------------------------------------------------------

    new_status, label = action_map[action]

    # ---------------------------------------------------------
    # UPDATE APPLICATION
    # ---------------------------------------------------------

    obj.status = new_status

    obj.current_remark = remark

    obj.save(
        update_fields=[
            "status",
            "current_remark",
            "updated_at",
        ]
    )

    # ---------------------------------------------------------
    # HISTORY
    # ---------------------------------------------------------

    ApplicationHistory.objects.create(
        application=obj,
        actor=request.user,
        action=label,
        remark=remark,
    )

    # ---------------------------------------------------------
    # NOTIFY STUDENT
    # ---------------------------------------------------------

    Notification.objects.create(
        user=obj.applicant,
        title=f"Application {label.lower()}",
        message=(
            f"{obj.application_id} is now "
            f"{obj.get_status_display()}. "
            f"{remark}"
        ).strip(),
        link=f"/applications/{obj.pk}/",
    )

    # ---------------------------------------------------------
    # AUDIT LOG
    # ---------------------------------------------------------

    AuditLog.objects.create(
        actor=request.user,
        action=f"APPLICATION_{action.upper()}",
        object_type="Application",
        object_id=str(obj.pk),
        details=remark,
    )

    # ---------------------------------------------------------
    # SUCCESS MESSAGE
    # ---------------------------------------------------------

    messages.success(
        request,
        (
            "Application marked as "
            f"{obj.get_status_display()}."
        ),
    )

    return redirect(
        "application_detail",
        pk=pk
    )