# In your 'fitness/models.py' file

from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Add other relevant fields like gender, fitness goals, etc.

    def __str__(self):
        return self.user.username

class Exercise(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    # Add fields for exercise type (e.g., cardio, strength), targeted muscle groups, etc.

    def __str__(self):
        return self.name

class Workout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username}'s workout on {self.date}"

class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sets = models.PositiveIntegerField(null=True, blank=True)
    reps = models.PositiveIntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Add fields for distance, duration (for cardio), etc. depending on exercise type

    def __str__(self):
        return f"{self.exercise.name} in {self.workout}"