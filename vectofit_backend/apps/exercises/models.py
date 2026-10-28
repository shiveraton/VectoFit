from typing import ClassVar

from django.db import models


class ExerciseVariant(models.Model):
    exercise_variant = models.CharField(max_length=50)

    class VariantType(models.TextChoices):
        BODYWEIGHT = "BW", "Bodyweight Squat"
        GOBLET = "GOB", "Goblet Squat"
        BARBELL = "BAR", "Barbell Squat"

    name = models.CharField(max_length=100, unique=True)
    variant_type = models.CharField(max_length=3, choices=VariantType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Untick to hide a variant (e.g. Barbell) from selection without deleting it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    min_knee_angle_deg = models.FloatField(default=90.0, help_text="Depth threshold")
    max_trunk_lean_deg = models.FloatField(default=45.0, help_text="Max forward lean")
    max_asymmetry_pct = models.FloatField(
        default=10.0, help_text="Max allowable L/R `%` diff"
    )

    def get_thresholds(self):
        return {
            "knee_depth": self.min_knee_angle_deg,
            "trunk_lean": self.max_trunk_lean_deg,
            "asymmetry": self.max_asymmetry_pct,
        }

    class Meta:
        ordering: ClassVar[list] = ["variant_type", "name"]

    def __str__(self):
        return self.name
