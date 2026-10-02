from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import MLModel, TrainingJob, EvaluationResult

from .serializers import MLModelSerializer, TrainingJobSerializer, EvaluationResultSerializer

class MLModelViewSet(viewsets.ModelViewSet):
    queryset = MLModel.objects.all()
    serializer_class = MLModelSerializer

    @action(detail=True, methods=["post"])
    def post(self, request, pk):
            # in the future, this would trigger a celery task
            try:
                ml_model = MLModel.objects.get(pk=pk)
                job = TrainingJob.objects.create(model=ml_model, status='PENDING')
                return Response(TrainingJobSerializer(job).data, status=status.HTTP_201_CREATED)
            except MLModel.DoesNotExist:
                return Response({"error": "Model not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"])
    def get(self, request, pk):
            evals = EvaluationResult.objects.filter(model_id=pk)
            serializer = EvaluationResultSerializer(evals, many=True)
            return Response(serializer.data)

class TrainingJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrainingJob.objects.all()
    serializer_class = TrainingJobSerializer

class AdministrationViewSet(viewsets.ModelViewSet):
    def get(self, request):
        return Response({
            'message': 'Administration API is working.'
        })
