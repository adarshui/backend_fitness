from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models import F

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_exercise_time = models.IntegerField(default=0, help_text="Total time spent in workouts, in seconds.")
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
    time_spent_today = models.IntegerField(default=0, help_text="Time spent active on the site today, in seconds.")


    class Meta:
        unique_together = ('user', 'date') # Ensure only one entry per user per day

    def __str__(self):
        return f"{self.user.username}'s stats for {self.date}"


class UserSessionActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=64, db_index=True)
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0, help_text="Computed when the user logs out.")
    date = models.DateField(default=timezone.now, help_text="Login date for daily aggregation.")
    
    class Meta:
        unique_together = ('user', 'session_key')
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} session on {self.date} ({self.duration_seconds}s)"


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    # Ensure we have a session key
    session_key = getattr(getattr(request, 'session', None), 'session_key', None)
    if not session_key and hasattr(request, 'session'):
        request.session.create()
        session_key = request.session.session_key
    if not session_key:
        session_key = f"no-session-{timezone.now().timestamp()}"
    # Create a new session activity record
    UserSessionActivity.objects.create(
        user=user,
        session_key=session_key,
        login_time=timezone.now(),
        date=timezone.now().date(),
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not user:
        return
    session_key = getattr(getattr(request, 'session', None), 'session_key', None)

    # Find the latest open session for this user (prefer matching session_key if available)
    qs = UserSessionActivity.objects.filter(user=user, logout_time__isnull=True)
    if session_key:
        qs = qs.filter(session_key=session_key)
    session = qs.order_by('-login_time').first()
    if not session:
        return

    session.logout_time = timezone.now()
    duration = int((session.logout_time - session.login_time).total_seconds())
    if duration < 0:
        duration = 0
    session.duration_seconds = duration
    session.save(update_fields=['logout_time', 'duration_seconds'])

    # Roll up to DailyUserStats for the session's login date
    daily, _ = DailyUserStats.objects.get_or_create(user=user, date=session.date)
    DailyUserStats.objects.filter(pk=daily.pk).update(time_spent_today=F('time_spent_today') + duration)