from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from applications.models import Application
from announcements.models import Announcement
from notifications.models import Notification


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return redirect("login")


@login_required
def dashboard(request):

    role = request.user.role

    # -----------------------------------------------------
    # KEEP EXISTING VISIBILITY LOGIC
    # -----------------------------------------------------

    if request.user.is_superuser or role in {
        "TEACHER",
        "STAFF",
        "HOD",
        "ADMIN",
    }:
        applications = Application.objects.all()
    else:
        applications = Application.objects.filter(
            applicant=request.user
        )

    # -----------------------------------------------------
    # APPLICATION STATISTICS
    # -----------------------------------------------------

    stats = (
        applications
        .values("status")
        .annotate(total=Count("id"))
    )

    stat_map = {
        item["status"]: item["total"]
        for item in stats
    }

    total = applications.count()

    pending = (
        stat_map.get("SUBMITTED", 0)
        + stat_map.get("UNDER_REVIEW", 0)
        + stat_map.get("FORWARDED", 0)
    )

    approved = (
        stat_map.get("APPROVED", 0)
        + stat_map.get("COMPLETED", 0)
    )

    rejected = stat_map.get("REJECTED", 0)

    completed = stat_map.get("COMPLETED", 0)

    # -----------------------------------------------------
    # NOTIFICATIONS
    # -----------------------------------------------------

    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False,
    )

    notifications = unread_notifications[:5]

    unread_notification_count = unread_notifications.count()

    # -----------------------------------------------------
    # ANNOUNCEMENTS
    # -----------------------------------------------------

    announcements = (
        Announcement.objects
        .filter(active=True)
        .order_by("-published_at")[:5]
    )

    # -----------------------------------------------------
    # RECENT APPLICATIONS
    # -----------------------------------------------------

    recent_applications = (
        applications
        .select_related(
            "applicant",
            "application_type",
        )
        .order_by("-created_at")[:8]
    )

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "completed": completed,

        "notifications": notifications,
        "unread_notification_count": unread_notification_count,

        "announcements": announcements,

        "recent_applications": recent_applications,

        "user_role": role,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )