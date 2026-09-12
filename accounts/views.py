from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from .forms import LoginForm, UserCreateForm, UserEditForm, SetPasswordForm
from .services import import_users_from_csv, import_users_from_excel
from .models import User


def is_admin(user):
    return bool(user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN))


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        messages.success(request, "Welcome to ME-ERP.")
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def profile(request):

    if request.method == "POST":

        signature = request.FILES.get("signature")

        if signature:
            request.user.signature = signature
            request.user.save(update_fields=["signature"])

            messages.success(
                request,
                "Signature uploaded successfully."
            )

        else:
            messages.error(
                request,
                "Please select a signature image."
            )

        return redirect("profile")

    return render(
        request,
        "accounts/profile.html"
    )

@login_required
def import_users_view(request):
    if request.user.role not in {User.Role.STAFF, User.Role.HOD, User.Role.ADMIN} and not request.user.is_superuser:
        raise PermissionDenied
    result = None
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        if not uploaded:
            messages.error(request, "Please choose a CSV or Excel file.")
        else:
            try:
                if uploaded.name.lower().endswith(".xlsx"):
                    result = import_users_from_excel(uploaded, request.user)
                else:
                    result = import_users_from_csv(uploaded, request.user)
                if result["errors"]:
                    messages.warning(request, f"Imported {result['imported']} users with {len(result['errors'])} row errors.")
                else:
                    messages.success(request, f"Imported {result['imported']} users successfully.")
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, "accounts/import_users.html", {"result": result})


@login_required
def user_list(request):
    if not is_admin(request.user):
        raise PermissionDenied
    users = User.objects.select_related("org_unit").order_by("-is_active_account", "role", "first_name")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        users = users.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(username__icontains=q) | Q(employee_or_student_id__icontains=q)
        )
    role_filter = request.GET.get("role", "").strip()
    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, "accounts/user_list.html", {
        "users": users, "q": q, "role_filter": role_filter, "roles": User.Role.choices,
    })


@login_required
def user_create(request):
    if not is_admin(request.user):
        raise PermissionDenied
    form = UserCreateForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Account created for {user.get_full_name() or user.username}.")
        return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "mode": "create"})


@login_required
def user_edit(request, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated {target.get_full_name() or target.username}.")
        return redirect("user_list")
    return render(request, "accounts/user_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def user_set_password(request, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(User, pk=pk)
    form = SetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        target.set_password(form.cleaned_data["new_password"])
        target.save(update_fields=["password"])
        messages.success(request, f"Password reset for {target.get_full_name() or target.username}.")
        return redirect("user_list")
    return render(request, "accounts/user_set_password.html", {"form": form, "target": target})


@login_required
def user_toggle_active(request, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("user_list")
    target.is_active_account = not target.is_active_account
    target.save(update_fields=["is_active_account"])
    state = "reactivated" if target.is_active_account else "deactivated"
    messages.success(request, f"{target.get_full_name() or target.username} has been {state}.")
    return redirect("user_list")


@login_required
def user_delete(request, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("user_list")
    if request.method == "POST":
        name = target.get_full_name() or target.username
        try:
            target.delete()
            messages.success(request, f"{name} has been permanently deleted.")
        except Exception:
            messages.error(
                request,
                f"Could not delete {name} - they have existing records (applications, "
                f"documents, etc.) linked to their account. Deactivate them instead to "
                f"preserve those records while blocking their login.",
            )
        return redirect("user_list")
    return render(request, "accounts/user_delete_confirm.html", {"target": target})
