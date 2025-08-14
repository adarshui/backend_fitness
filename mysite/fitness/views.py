from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import UserProfile

@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, email=email, password=password)
    return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    return Response({
        'message': f'Welcome {request.user.username}!',
        'stats': {
            'total_workouts': 12,
            'calories_burned': 2450,
            'active_days': 8
        },
        'recent_activities': [
            {'name': 'Morning Run', 'date': '2024-01-15', 'calories': 300},
            {'name': 'Weight Training', 'date': '2024-01-14', 'calories': 250},
            {'name': 'Yoga Session', 'date': '2024-01-13', 'calories': 150}
        ]
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return Response({
        'username': request.user.username,
        'email': request.user.email,
        'total_exercise_time': profile.total_exercise_time,
        'total_workouts': profile.total_workouts,
        'goals': {
            'weekly_workouts': 5,
            'target_calories': 2000
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_workout(request):
    exercise_time = request.data.get('exercise_time', 0)  # in seconds
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.total_exercise_time += exercise_time
    profile.total_workouts += 1
    profile.save()
    
    return Response({
        'total_exercise_time': profile.total_exercise_time,
        'total_workouts': profile.total_workouts,
        'message': 'Workout tracked successfully'
    })