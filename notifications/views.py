from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Notification


@login_required
def notification_list(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "notifications/list.html",
        {
            "notifications": notifications,
        },
    )


@login_required
def mark_notification_read(request, notification_id):

    if request.method == "POST":

        notification = Notification.objects.filter(
            id=notification_id,
            user=request.user,
        ).first()

        if notification:

            notification.is_read = True

            notification.save(
                update_fields=["is_read"]
            )

            if notification.link:
                return redirect(notification.link)

    return redirect("notification_list")


@login_required
def mark_all_notifications_read(request):

    if request.method == "POST":

        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(
            is_read=True
        )

    return redirect("notification_list")