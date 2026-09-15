from django.contrib import admin
from .models import ApplicationType, Application, ApplicationHistory


@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "default_authority_role", "route_to_admin_office", "active")
    list_filter = ("default_authority_role", "route_to_admin_office", "active")

admin.site.register(Application)
admin.site.register(ApplicationHistory)
