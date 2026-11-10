from django.urls import path
from .views import ValidationMediaView, ValidationRatingView, ValidationSampleView

urlpatterns = [
    path("sample/", ValidationSampleView.as_view(), name="validation-sample"),
    path("annotations/<int:repetition_id>/", ValidationRatingView.as_view(), name="validation-rating"),
    path("media/<int:sample_id>/", ValidationMediaView.as_view(), name="validation-media"),
]
