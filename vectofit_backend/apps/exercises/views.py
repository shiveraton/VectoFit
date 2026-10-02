from django.shortcuts import render
from django.utils import timezone
from rest_framework import permissions, viewsets

from .models import ExerciseVariant
from .serializers import ExerciseVariantSerializer

class ExerciseVariantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExerciseVariant.objects.all()
    serializer_class = ExerciseVariantSerializer
    permission_classes = [permissions.IsAuthenticated]