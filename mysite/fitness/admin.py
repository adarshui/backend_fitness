from django.contrib import admin
from .models import UserProfile, Exercise, Workout, WorkoutExercise

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight', 'height', 'date_of_birth']
    list_filter = ['date_of_birth']

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'duration_minutes']
    list_filter = ['date', 'user']
    date_hierarchy = 'date'

@admin.register(WorkoutExercise)
class WorkoutExerciseAdmin(admin.ModelAdmin):
    list_display = ['workout', 'exercise', 'sets', 'reps', 'weight']
    list_filter = ['exercise', 'workout__date']