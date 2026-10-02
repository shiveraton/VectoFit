from django.db import models
from django.utils import timezone

class MLModel(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "ML Model"
        unique_together = ('name', 'version')

    def __str__(self):
        return f"{self.name} v{self.version}"

class TrainingJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='training_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    logs = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Job for {self.model} - {self.status}"

class EvaluationResult(models.Model):
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='evaluations')
    accuracy = models.FloatField()
    f1_score = models.FloatField()
    test_dataset_version = models.CharField(max_length=50)
    evaluated_at = models.DateTimeField(default=timezone.now)
    metrics_report = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-evaluated_at']