from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    # Get username and email from the related User model as read-only
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        # Define the fields to include in the API response/request
        fields = [
            'username', 
            'email', 
            'age', 
            'gender', 
            'height', 
            'weight', 
            'level', 
            'date_of_birth'
        ]