from django.urls import path
from .views import (
    org_unit_list, org_unit_create, org_unit_edit,
    org_unit_toggle_active, org_unit_import,
)

urlpatterns = [
    path("", org_unit_list, name="org_unit_list"),
    path("new/", org_unit_create, name="org_unit_create"),
    path("<int:pk>/edit/", org_unit_edit, name="org_unit_edit"),
    path("<int:pk>/toggle-active/", org_unit_toggle_active, name="org_unit_toggle_active"),
    path("import/", org_unit_import, name="org_unit_import"),
]
