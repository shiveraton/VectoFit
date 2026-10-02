from django.db import models
from django.conf import settings

from apps.exercises.models import ExerciseVariant

class BodyProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="body_profile"
    )
    height_cm = models.FloatField()
    torso_length_cm = models.FloatField()
    femur_length_cm = models.FloatField()
    tibia_length_cm = models.FloatField()
    scale_factor = models.FloatField(
        help_text="Pixel-to-metric scale factor derived during calibrate_frame()."
    )
    raw_calibration_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Frame-by-frame landmarks and raw confidence vectors from calibration.",
    )
    calibrated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calibrated_at"]

    def __str__(self):
        return f"{self.user} profile ({self.calibrated_at:%Y-%m-%d})"

class AssessmentSession(models.Model):
    """a single recorded squat assessment (one uploaded video)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", 'Pending'
        PROCESSING = "PROCESSING", 'Processing'
        COMPLETED = "COMPLETED", 'Completed'
        FAILED = "FAILED", 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_sessions"
    )
    exercise_variant = models.ForeignKey(
        ExerciseVariant,
        on_delete=models.PROTECT,
        related_name="sessions"
    )
    body_profile = models.ForeignKey(
        BodyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        help_text="Snapshot of which calibration was active for this session."
    )
    video_file = models.FileField(upload_to="assessments_videos/%Y/%m/%d/")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

        def __str__(self):
            return f"Session {self.pk} - {self.user} ({self.status})"

class RepAssessment(models.Model):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="reps"
    )
    rep_number = models.PositiveSmallIntegerField()

    jaa_score = models.FloatField(null=True, blank=True, help_text="Joint Angle Analysis")
    rom_score = models.FloatField(null=True, blank=True, help_text="Range of Motion")
    bad_score = models.FloatField(null=True, blank=True, help_text="Bilateral Asymmetry Detection")
    kvt_score = models.FloatField(null=True, blank=True, help_text="Kinematic Velocity Tracking")

    hybrid_score = models.FloatField(null=True, blank=True)
    classification = models.CharField(max_length=50, blank=True)

    landmark_series = models.JSONField(
        help_text="Numeric landmark coordinate time-series for this rep's frame window. No raw frames are stored."
    )
    start_frame = models.PositiveIntegerField(null=True, blank=True)
    end_frame = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["session", "rep_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "rep_number"], name="unique_rep_per_session"
            )
        ]

def __str__(self):
    return f"Rep {self.rep_number} of session {self.session_id}"