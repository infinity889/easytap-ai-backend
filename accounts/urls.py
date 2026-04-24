from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AssistantChatView,
    AssistantChannelChatView,
    AdminCandidatesView,
    GoogleLoginView,
    JobMatchesView,
    LoginView,
    LogoutView,
    MeView,
    ProfileView,
    GoogleCallbackView,
    RegisterView,
    SkillDetailView,
    SkillListCreateView,
    TelegramLinkConfirmView,
    TelegramLinkStartView,
    TelegramLinkStatusView,
    VacancyCatalogView,
)


urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="auth-google-callback"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("skills/", SkillListCreateView.as_view(), name="skills"),
    path("skills/<uuid:pk>/", SkillDetailView.as_view(), name="skill-detail"),
    path("jobs/matches/", JobMatchesView.as_view(), name="job-matches"),
    path("jobs/catalog/", VacancyCatalogView.as_view(), name="job-catalog"),
    path("assistant/chat/", AssistantChatView.as_view(), name="assistant-chat"),
    path("assistant/channel-chat/", AssistantChannelChatView.as_view(), name="assistant-channel-chat"),
    path("tg/link/start/", TelegramLinkStartView.as_view(), name="tg-link-start"),
    path("tg/link/confirm/", TelegramLinkConfirmView.as_view(), name="tg-link-confirm"),
    path("tg/link/status/", TelegramLinkStatusView.as_view(), name="tg-link-status"),
    path("admin/candidates/", AdminCandidatesView.as_view(), name="admin-candidates"),
]
