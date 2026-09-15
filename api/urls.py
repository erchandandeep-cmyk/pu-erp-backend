from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import login_api, me_api, import_users_api, authorities_api, suggest_authority_api, my_results_api, ApplicationTypeViewSet, ApplicationViewSet, AnnouncementViewSet
from organizations.views import OrgUnitViewSet
router = DefaultRouter()
router.register("application-types", ApplicationTypeViewSet, basename="application-type")
router.register("applications", ApplicationViewSet, basename="application")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("org-units", OrgUnitViewSet, basename="org-unit")
urlpatterns = [
    path("login/", login_api, name="api_login"),
    path("me/", me_api, name="api_me"),
    path("authorities/", authorities_api, name="api_authorities"),
    path("authorities/suggest/", suggest_authority_api, name="api_suggest_authority"),
    path("my-results/", my_results_api, name="api_my_results"),
    path("users/import/", import_users_api, name="api_import_users"),
    path("", include(router.urls)),
]

