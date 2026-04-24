from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminCandidatesView,
    GoogleLoginView,
    JobMatchesView,
    LoginView,
    LogoutView,
    MeView,
    ProfileView,
    RegisterView,
    SkillDetailView,
    SkillListCreateView,
)


urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("skills/", SkillListCreateView.as_view(), name="skills"),
    path("skills/<uuid:pk>/", SkillDetailView.as_view(), name="skill-detail"),
    path("jobs/matches/", JobMatchesView.as_view(), name="job-matches"),
    path("admin/candidates/", AdminCandidatesView.as_view(), name="admin-candidates"),
]
