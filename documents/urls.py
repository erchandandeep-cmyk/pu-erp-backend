from django.urls import path
from .views import document_list
urlpatterns = [path("", document_list, name="document_list")]
