from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_exercise_time = models.IntegerField(default=0)
    total_workouts = models.IntegerField(default=0)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, default='')
    level = models.CharField(max_length=20, default='beginner')

    def __str__(self):
        return self.user.username

class DailyUserStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    calories_burned = models.FloatField(default=0)
    weight = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'date') # Ensure only one entry per user per day

    def __str__(self):
        return f"{self.user.username}'s stats for {self.date}"