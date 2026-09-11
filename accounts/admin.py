from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Department details", {"fields": ("role", "employee_or_student_id", "phone", "department", "org_unit", "semester", "section", "is_active_account")}),
    )
    list_display = ("username", "employee_or_student_id", "first_name", "last_name", "role", "org_unit", "is_active_account", "is_staff")
    list_filter = ("role", "org_unit", "is_active_account", "is_staff")
    autocomplete_fields = ("org_unit",)
