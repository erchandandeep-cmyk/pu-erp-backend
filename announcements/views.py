from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from .forms import AnnouncementForm
from .models import Announcement
from accounts.models import User
from notifications.models import Notification
from audit.models import AuditLog

def can_publish(user):
    return user.is_superuser or user.role in {"TEACHER", "STAFF", "HOD", "ADMIN"}

@login_required
def announcement_list(request):
    qs = Announcement.objects.filter(active=True).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=timezone.now())
    ).select_related("published_by")
    audience = {
        User.Role.STUDENT: {"ALL", "STUDENTS"},
        User.Role.TEACHER: {"ALL", "TEACHERS"},
        User.Role.STAFF: {"ALL", "STAFF"},
        User.Role.HOD: {"ALL", "HOD"},
        User.Role.ADMIN: {"ALL"},
    }[request.user.role] if not request.user.is_superuser else {"ALL", "STUDENTS", "TEACHERS", "STAFF", "HOD"}
    qs = qs.filter(audience__in=audience)
    return render(request, "announcements/list.html", {"announcements": qs})

@login_required
def create_announcement(request):
    if not can_publish(request.user):
        raise PermissionDenied
    form = AnnouncementForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.published_by = request.user
        obj.save()
        role_map = {"ALL": User.objects.filter(is_active=True), "STUDENTS": User.objects.filter(role="STUDENT", is_active=True), "TEACHERS": User.objects.filter(role="TEACHER", is_active=True), "STAFF": User.objects.filter(role="STAFF", is_active=True), "HOD": User.objects.filter(role="HOD", is_active=True)}
        for user in role_map[obj.audience]:
            Notification.objects.create(user=user, title="New announcement", message=obj.title, link="/announcements/")
        AuditLog.objects.create(actor=request.user, action="ANNOUNCEMENT_CREATED", object_type="Announcement", object_id=str(obj.pk), details=obj.title)
        messages.success(request, "Announcement published.")
        return redirect("announcement_list")
    return render(request, "announcements/form.html", {"form": form})
