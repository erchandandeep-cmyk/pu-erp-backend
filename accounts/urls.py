from django.urls import path
from .views import (
    login_view, logout_view, profile, import_users_view,
    user_list, user_create, user_edit, user_set_password,
    user_toggle_active, user_delete,
)
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile, name="profile"),
    path("import-users/", import_users_view, name="import_users"),
    path("users/", user_list, name="user_list"),
    path("users/new/", user_create, name="user_create"),
    path("users/<int:pk>/edit/", user_edit, name="user_edit"),
    path("users/<int:pk>/set-password/", user_set_password, name="user_set_password"),
    path("users/<int:pk>/toggle-active/", user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/delete/", user_delete, name="user_delete"),
]
