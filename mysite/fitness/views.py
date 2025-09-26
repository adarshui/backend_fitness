from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import UserProfile, DailyUserStats
from datetime import timedelta
from django.utils import timezone

@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    gender = request.data.get('gender')
    weight = request.data.get('weight')
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    if email and User.objects.filter(email__iexact=email).exists():
        return Response({'error': 'An account with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, email=email, password=password)

    # Ensure empty strings for optional fields are saved as NULL
    gender_to_save = gender if gender else None
    weight_to_save = weight if weight else None

    # Create UserProfile with optional gender and weight
    UserProfile.objects.create(user=user, gender=gender_to_save, weight=weight_to_save)

    return Response({'message': 'User created successfully. Please log in.'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    # Get summary stats from UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get daily stats for the last 30 days
    today = timezone.now().date()
    start_date = today - timedelta(days=29)
    
    daily_stats_qs = DailyUserStats.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by('date')

    # Create a dictionary for quick lookups
    stats_dict = {s.date.strftime('%Y-%m-%d'): s for s in daily_stats_qs}

    # Prepare data for charts, filling in missing days
    chart_data = []
    
    # Find the most recent weight entry to back-fill from
    most_recent_stat_with_weight = DailyUserStats.objects.filter(
        user=request.user, 
        date__lt=start_date, 
        weight__isnull=False
    ).order_by('-date').first()
    
    last_known_weight = profile.weight
    if most_recent_stat_with_weight:
        last_known_weight = most_recent_stat_with_weight.weight

    for i in range(30):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        
        stat = stats_dict.get(date_str)
        
        calories = stat.calories_burned if stat and stat.calories_burned is not None else 0
        
        # Use the stat's weight if available, otherwise carry over the last known weight
        if stat and stat.weight is not None:
            weight = stat.weight
            last_known_weight = weight
        else:
            weight = last_known_weight

        chart_data.append({
            'date': current_date.strftime('%b %d'), # Format for display, e.g., "Sep 06"
            'calories_burned': calories,
            'weight': weight if weight is not None else None # can be null if never entered
        })

    # Calculate total calories burned in the last 30 days
    from django.db.models import Sum
    total_calories_30_days = daily_stats_qs.aggregate(total_calories=Sum('calories_burned'))['total_calories'] or 0

    # Get today's stats from the data we already fetched
    today_stat = stats_dict.get(today.strftime('%Y-%m-%d'))
    calories_today = 0
    seconds_today = 0
    workouts_today = 0
    minutes_today = 0
    if today_stat:
        calories_today = today_stat.calories_burned or 0
        # Assumes `time_spent_today` is stored in seconds in the database
        seconds_today = (getattr(today_stat, 'time_spent_today', 0) or 0)
        workouts_today = getattr(today_stat, 'workouts_today', 0) or 0
        minutes_today = seconds_today // 60

    return Response({
        'message': f'Welcome {request.user.username}!',
        'summary_stats': {
            'total_workouts': profile.total_workouts,
            'total_calories': total_calories_30_days,
            'total_minutes': minutes_today,
            'time_spent_seconds': seconds_today,
            'current_weight': profile.weight,
            'day_streak': 0, # Placeholder for now
            'calories_today': calories_today,
            'workouts_today': workouts_today,
        },
        'chart_data': chart_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_activity(request):
    """
    Logs user activity by incrementing time spent.
    Expects 'seconds' in the request data.
    """
    seconds = request.data.get('seconds', 0)
    
    try:
        seconds = int(seconds)
        if seconds <= 0:
            return Response({'error': 'Invalid seconds value'}, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid seconds value'}, status=status.HTTP_400_BAD_REQUEST)

    # Get or create a daily stats record for today
    today = timezone.now().date()
    daily_stats, created = DailyUserStats.objects.get_or_create(
        user=request.user,
        date=today
    )
    
    # Use an F() expression for a safe, atomic update directly in the database.
    # This avoids race conditions and correctly handles cases where the field might be null.
    from django.db.models import F
    daily_stats.time_spent_today = F('time_spent_today') + seconds
    daily_stats.save(update_fields=['time_spent_today'])
    
    return Response({'message': 'Activity logged'}, status=status.HTTP_200_OK)

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_workout(request):
    """
    Updates daily stats for a user after completing a workout.
    Accepts 'calories_burned'.
    """
    calories = request.data.get('calories_burned')

    if calories is None:
        return Response({'error': 'calories_burned is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        calories = float(calories)
        if calories < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return Response({'error': 'calories_burned must be a non-negative number'}, status=status.HTTP_400_BAD_REQUEST)

    # Get or create a daily stats record for today
    today = timezone.now().date()
    daily_stats, created = DailyUserStats.objects.get_or_create(
        user=request.user,
        date=today
    )

    # Atomically update stats for today
    from django.db.models import F
    DailyUserStats.objects.filter(pk=daily_stats.pk).update(
        calories_burned=F('calories_burned') + calories,
        workouts_today=F('workouts_today') + 1
    )
    # Also increment the total workout count on the user's profile
    from django.db.models import F
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.total_workouts = F('total_workouts') + 1
    profile.save(update_fields=['total_workouts'])

    return Response({
        'message': f'Great job! {calories:.0f} calories added to your daily total.',
        'date': daily_stats.date,
        # Return the new total, since the daily_stats object is stale after .update()
        'total_calories_today': (daily_stats.calories_burned or 0) + calories
    }, status=status.HTTP_200_OK)

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
        new_weight = request.data.get('weight')
        if new_weight is not None:
            profile.weight = new_weight
            # Also update today's daily stats with the new weight
            today = date.today()
            daily_stats, created = DailyUserStats.objects.get_or_create(user=request.user, date=today)
            try:
                daily_stats.weight = float(profile.weight)
                daily_stats.save()
            except (ValueError, TypeError):
                pass # Ignore if weight is not a valid float
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