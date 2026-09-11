from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from .forms import LoginForm
from .services import import_users_from_csv
from .models import User

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
            messages.error(request, "Please choose a CSV file.")
        else:
            try:
                result = import_users_from_csv(uploaded, request.user)
                if result["errors"]:
                    messages.warning(request, f"Imported {result['imported']} users with {len(result['errors'])} row errors.")
                else:
                    messages.success(request, f"Imported {result['imported']} users successfully.")
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, "accounts/import_users.html", {"result": result})
