from django.urls import path

from . import views

urlpatterns = [
    path("classifier/", views.ClassifierAPIView.as_view(), name="classifier"),
]
