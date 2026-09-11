from django.urls import path
from .views import (
    application_list,
    create_application,
    application_detail,
    application_action,
    application_pdf,
)
urlpatterns = [
    path("", application_list, name="application_list"),
    path("new/", create_application, name="create_application"),
    path("<int:pk>/", application_detail, name="application_detail"),
     path(
        "<int:pk>/pdf/",
        application_pdf,
        name="application_pdf",
    ),
    path("<int:pk>/<str:action>/", application_action, name="application_action"),
]
