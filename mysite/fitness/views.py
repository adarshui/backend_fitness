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

# get user profile
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return Response({
        'username': request.user.username,
        'email': request.user.email,
        'date_of_birth': profile.date_of_birth,
        'age': profile.age,
        'weight': profile.weight,
        'height': profile.height,
        'gender': profile.gender,
        'level': profile.level
    })
    
    
# Level normalization and video configurations
ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}

def normalize_level(level):
    """Normalize various forms of level input to canonical strings: beginner|intermediate|advanced."""
    s = str(level).strip().lower() if level is not None else ""
    if s in ("1", "beginner"):
        return "beginner"
    if s in ("2", "intermediate"):
        return "intermediate"
    if s in ("3", "advanced"):
        return "advanced"
    # Default/fallback
    return "beginner"

# Define your videos with per-level sets and calories per set
WORKOUT_VIDEOS = [
    {
        "id": "warmup",
        "title": "Full Body Warm-up",
        "sets": {"beginner": 2, "intermediate": 3, "advanced": 4},
        "calories_per_set": {"beginner": 20, "intermediate": 25, "advanced": 30}
    },
    {
        "id": "jjacks",
        "title": "Jumping Jacks",
        "sets": {"beginner": 3, "intermediate": 4, "advanced": 5},
        "calories_per_set": {"beginner": 30, "intermediate": 40, "advanced": 55}
    },
    {
        "id": "squats",
        "title": "Bodyweight Squats",
        "sets": {"beginner": 2, "intermediate": 3, "advanced": 5},
        "calories_per_set": {"beginner": 35, "intermediate": 45, "advanced": 60}
    },
    {
        "id": "pushups",
        "title": "Push-ups",
        "sets": {"beginner": 2, "intermediate": 3, "advanced": 4},
        "calories_per_set": {"beginner": 25, "intermediate": 35, "advanced": 50}
    },
    {
        "id": "plank",
        "title": "Plank Holds",
        "sets": {"beginner": 2, "intermediate": 3, "advanced": 4},
        "calories_per_set": {"beginner": 15, "intermediate": 20, "advanced": 28}
    }
]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def videos(request):
    """
    Return videos adjusted to the authenticated user's level, including sets and calories per set
    and total calories for those sets.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_level = normalize_level(getattr(profile, 'level', 'beginner'))

    payload = []
    for v in WORKOUT_VIDEOS:
        sets = v["sets"].get(user_level, v["sets"]["beginner"])  # fallback safe
        cal_per_set = v["calories_per_set"].get(user_level, v["calories_per_set"]["beginner"])  # fallback safe
        payload.append({
            "id": v["id"],
            "title": v["title"],
            "level": user_level,
            "sets": sets,
            "calories_per_set": cal_per_set,
            "total_calories": sets * cal_per_set
        })

    return Response({"videos": payload})

from datetime import date
from rest_framework import status

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_user_profile(request):
    """
    Save or update the authenticated user's profile.
    - Accepts: date_of_birth (YYYY-MM-DD), age, weight, height, gender, level
    - If age is not provided (or is empty) but date_of_birth is available (from request or existing profile),
      age is computed and saved based on date_of_birth.
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # 1) Handle and validate date_of_birth
    dob_input = request.data.get('date_of_birth', None)
    dob_to_set = profile.date_of_birth  # default to existing if not provided

    if dob_input is not None:
        # Allow clearing dob with empty string
        if isinstance(dob_input, str) and dob_input.strip() == '':
            dob_to_set = None
        else:
            try:
                if isinstance(dob_input, date):
                    dob_to_set = dob_input
                else:
                    # Expect ISO format YYYY-MM-DD
                    dob_to_set = date.fromisoformat(str(dob_input))
            except (TypeError, ValueError):
                return Response(
                    {'error': 'Invalid date_of_birth format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Future date guard
        if dob_to_set and dob_to_set > date.today():
            return Response(
                {'error': 'date_of_birth cannot be in the future.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    profile.date_of_birth = dob_to_set

    # 2) Handle age: compute from dob if not provided
    age_input = request.data.get('age', None)
    age_to_set = None
    age_missing = age_input is None or (isinstance(age_input, str) and age_input.strip() == '')

    if age_missing:
        if profile.date_of_birth:
            today = date.today()
            computed_age = (
                today.year
                - profile.date_of_birth.year
                - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
            )
            age_to_set = computed_age
        # If no dob, we leave age unchanged
    else:
        try:
            age_to_set = int(age_input)
            if age_to_set < 0:
                return Response(
                    {'error': 'age must be a non-negative integer.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (TypeError, ValueError):
            return Response(
                {'error': 'age must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    if age_to_set is not None:
        profile.age = age_to_set

    # 3) Other fields: weight, height, gender
    # Preserve existing values if not provided
    if 'weight' in request.data:
        profile.weight = request.data.get('weight', profile.weight)
    if 'height' in request.data:
        profile.height = request.data.get('height', profile.height)
    if 'gender' in request.data:
        profile.gender = request.data.get('gender', profile.gender)

    # 4) Handle level (normalize and store as canonical string)
    level_input = request.data.get('level', None)
    if level_input is not None:
        profile.level = normalize_level(level_input)

    profile.save()
    return Response({'message': 'Profile updated successfully'})