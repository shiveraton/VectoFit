from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True)
    is_annotator = models.BooleanField(default=False)
    is_validator = models.BooleanField(default=False)
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", default="default.jpg"
    )

    def __str__(self):
        return f"{self.user.username} Profile"

    height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        SIGN_IN = "sign_in", "Signed in"
        REGISTERED = "registered", "Account registered"
        ACCOUNT_UPDATED = "account_updated", "Account updated"

    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=32, choices=Action.choices)
    details = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
