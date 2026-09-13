from django.urls import path
from . import views

urlpatterns = [
    path("sessions/", views.session_list, name="session_list"),
    path("sessions/new/", views.session_create, name="session_create"),
    path("sessions/<int:pk>/edit/", views.session_edit, name="session_edit"),

    path("programmes/", views.programme_list, name="programme_list"),
    path("programmes/new/", views.programme_create, name="programme_create"),
    path("programmes/<int:pk>/edit/", views.programme_edit, name="programme_edit"),
    path("programmes/<int:pk>/toggle-active/", views.programme_toggle_active, name="programme_toggle_active"),

    path("enrollments/", views.enrollment_list, name="enrollment_list"),
    path("enrollments/new/", views.enrollment_create, name="enrollment_create"),
    path("enrollments/<int:pk>/edit/", views.enrollment_edit, name="enrollment_edit"),
    path("enrollments/import/", views.enrollment_import, name="enrollment_import"),
]
