from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg')

    def __str__(self):
        return f'{self.user.username} Profile'

    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
