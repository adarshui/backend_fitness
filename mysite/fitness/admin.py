from django.contrib import admin
from .models import UserProfile, DailyUserStats

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight', 'height', 'date_of_birth', 'total_exercise_time', 'total_workouts']
    list_filter = ['date_of_birth']
    
@admin.register(DailyUserStats)
class DailyUserStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'calories_burned', 'weight', 'time_spent_today']
    list_filter = ['date']
    search_fields = ['user__username']
