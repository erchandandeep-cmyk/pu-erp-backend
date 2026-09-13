from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from dashboard.views import home

urlpatterns = [
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
