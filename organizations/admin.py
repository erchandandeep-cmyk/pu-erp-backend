from django.contrib import admin

from .models import OrgUnit


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "unit_type", "parent", "is_active")
    list_filter = ("unit_type", "is_active")
    search_fields = ("name", "code")
    ordering = ("unit_type", "name")
