from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, default='')
    height = models.FloatField(null=True, blank=True) # in cm
    weight = models.FloatField(null=True, blank=True) # in kg
    level = models.CharField(max_length=20, blank=True, default='beginner')
    date_of_birth = models.DateField(null=True, blank=True)
    total_exercise_time = models.IntegerField(default=0) # in seconds
    total_workouts = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

# These functions (signals) ensure a UserProfile is created when a new User signs up.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)