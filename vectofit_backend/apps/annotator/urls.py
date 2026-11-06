from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view()),
    path("register/", views.RegisterView.as_view()),
    path("login/", views.LoginView.as_view()),
    path("me/", views.MeView.as_view()),
    path("logout/", views.LogoutView.as_view()),
    path("datasets/", views.DatasetListView.as_view()),
    path("datasets/<int:dataset_id>/session/", views.SessionView.as_view()),
    path("samples/<int:sample_id>/rating/", views.RatingView.as_view()),
    path("videos/<int:video_id>/", views.VideoView.as_view()),
]
