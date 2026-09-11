from django.contrib import admin
from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    """
    This is where new departments, regional centres, constituent
    colleges, neighbourhood campuses and affiliated colleges get added
    as the app grows beyond Mechanical Engineering — no code changes
    needed, just add a row here.
    """

    list_display = ("name", "kind", "code", "parent", "city", "is_active")
    list_filter = ("kind", "is_active", "city")
    search_fields = ("name", "code", "city")
    autocomplete_fields = ("parent",)
    ordering = ("kind", "name")
