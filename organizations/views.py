from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import OrgUnit
from .forms import OrgUnitForm
from .services import import_org_units_from_csv
from .serializers import OrgUnitSerializer


def _is_admin(user):
    from accounts.models import User
    return bool(user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN))


@login_required
def org_unit_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    units = OrgUnit.objects.select_related("parent").order_by("unit_type", "name")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        units = units.filter(Q(name__icontains=q) | Q(code__icontains=q))
    type_filter = request.GET.get("type", "").strip()
    if type_filter:
        units = units.filter(unit_type=type_filter)
    return render(request, "organizations/org_unit_list.html", {
        "units": units, "q": q, "type_filter": type_filter, "unit_types": OrgUnit.UnitType.choices,
    })


@login_required
def org_unit_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = OrgUnitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        unit = form.save()
        messages.success(request, f"Created '{unit.name}'.")
        return redirect("org_unit_list")
    return render(request, "organizations/org_unit_form.html", {"form": form, "mode": "create"})


@login_required
def org_unit_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(OrgUnit, pk=pk)
    form = OrgUnitForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated '{target.name}'.")
        return redirect("org_unit_list")
    return render(request, "organizations/org_unit_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def org_unit_toggle_active(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    target = get_object_or_404(OrgUnit, pk=pk)
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    state = "reactivated" if target.is_active else "deactivated"
    messages.success(request, f"'{target.name}' has been {state}.")
    return redirect("org_unit_list")


@login_required
def org_unit_import(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    result = None
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        if not uploaded:
            messages.error(request, "Please choose a CSV file.")
        else:
            try:
                result = import_org_units_from_csv(uploaded)
                if result["errors"]:
                    messages.warning(request, f"Imported: {result['created']} created, {result['updated']} updated, {len(result['errors'])} row problems.")
                else:
                    messages.success(request, f"Imported: {result['created']} created, {result['updated']} updated.")
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, "organizations/org_unit_import.html", {"result": result})


class OrgUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only list of active org units, so the login/registration
    screen (web or mobile) can show a department/college dropdown before
    the user is authenticated.
    """

    queryset = OrgUnit.objects.filter(is_active=True).select_related("parent")
    serializer_class = OrgUnitSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["unit_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        unit_type = self.request.query_params.get("unit_type")
        if unit_type:
            qs = qs.filter(unit_type=unit_type.upper())
        return qs.order_by("unit_type", "name")
