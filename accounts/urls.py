from django.urls import path
from .views import login_view, logout_view, profile, import_users_view
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile, name="profile"),
    path("import-users/", import_users_view, name="import_users"),
]
