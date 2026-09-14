from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from dashboard.views import home


def api_root_status(request):
    """
    A neutral machine-readable status endpoint, as recommended by the
    live gap analysis - lets monitoring tools / uptime checks confirm
    the API is alive without hitting a human-facing login page.
    """
    return JsonResponse({
        "system": "Punjabi University ERP",
        "status": "operational",
    })


urlpatterns = [
    path("api/status/", api_root_status, name="api_status"),
    path("api/", include("api.urls")),
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("org-units/", include("organizations.urls")),
    path("academics/", include("academics.urls")),
    path("applications/", include("applications.urls")),
    path("announcements/", include("announcements.urls")),
    path("documents/", include("documents.urls")),
    path("notifications/", include("notifications.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
