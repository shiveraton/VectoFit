from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.datasets.services.knee_label import knee_target


class ValidationSample(models.Model):
    repetition = models.OneToOneField("datasets.DatasetSample", on_delete=models.PROTECT)
    position = models.PositiveIntegerField(unique=True)
    protocol_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "pk"]


class AuditedAnnotationQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Save validation annotations individually to preserve history.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Save validation annotations individually to preserve history.")

    def delete(self):
        raise ValidationError("Validation annotations are retained with their history.")


class ValidationAnnotation(models.Model):
    class Knee(models.TextChoices):
        ALIGNED = "aligned", "Aligned"
        BORDERLINE = "borderline", "Borderline"
        DEVIATED = "deviated", "Deviated"
        UNASSESSABLE = "unassessable", "Unassessable"

    repetition = models.ForeignKey("datasets.DatasetSample", on_delete=models.PROTECT)
    validator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    left_knee = models.CharField(max_length=16, choices=Knee.choices)
    right_knee = models.CharField(max_length=16, choices=Knee.choices)
    overall = models.CharField(max_length=16, editable=False)
    notes = models.TextField(blank=True)
    protocol_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = AuditedAnnotationQuerySet.as_manager()

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["repetition", "validator"], name="unique_validation_repetition_validator",
        )]

    def save(self, *args, **kwargs):
        self.overall = knee_target({"left": {"grade": self.left_knee},
                                    "right": {"grade": self.right_knee}})
        if self.overall == "incomplete":
            raise ValidationError("Both knee grades are required and must be valid.")
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"overall"}
        with transaction.atomic():
            super().save(*args, **kwargs)
            ValidationAnnotationEvent.objects.create(
                annotation=self,
                payload={"repetition_id": self.repetition_id, "validator_id": self.validator_id,
                         "left_knee": self.left_knee, "right_knee": self.right_knee,
                         "overall": self.overall, "notes": self.notes,
                         "protocol_version": self.protocol_version},
            )

    def delete(self, *args, **kwargs):
        raise ValidationError("Validation annotations are retained with their history.")


class AppendOnlyQuerySet(models.QuerySet):
    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Append validation history individually.")

    def update(self, **kwargs):
        raise ValidationError("Validation history is append-only.")

    def delete(self):
        raise ValidationError("Validation history is append-only.")


class ValidationAnnotationEvent(models.Model):
    annotation = models.ForeignKey(ValidationAnnotation, on_delete=models.PROTECT, related_name="events")
    source = models.CharField(max_length=16, default="validation", editable=False)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "pk"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Validation history is append-only.")
        self.source = "validation"
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Validation history is append-only.")
