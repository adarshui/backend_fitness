from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', views.register_user, name='register'),
    path('api/dashboard/', views.dashboard_data, name='dashboard_data'),
    path('api/profile/', views.user_profile, name='user_profile'),
    path('api/track-workout/', views.track_workout, name='track_workout'),
]