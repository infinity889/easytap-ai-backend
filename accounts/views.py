from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile, Skill, User
from .permissions import IsAdminRole
from .serializers import (
    AdminCandidateSerializer,
    CareerTokenObtainPairSerializer,
    JobMatchSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SkillSerializer,
    UserSerializer,
)
from .services import build_admin_candidates, build_job_matches


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = CareerTokenObtainPairSerializer.get_token(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CareerTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_205_RESET_CONTENT)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        callback_url = settings.FRONTEND_GOOGLE_CALLBACK_URL
        params = urlencode({"error": "Google OAuth is not configured yet."})
        return redirect(f"{callback_url}?{params}")


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    def get_object(self, user: User) -> Profile:
        try:
            return user.profile
        except Profile.DoesNotExist as exc:
            raise Http404 from exc

    def get(self, request):
        profile = self.get_object(request.user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SkillListCreateView(generics.ListCreateAPIView):
    serializer_class = SkillSerializer

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SkillSerializer

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user)


class JobMatchesView(APIView):
    def get(self, request):
        profile = Profile.objects.filter(user=request.user).first()
        skills = list(Skill.objects.filter(user=request.user))
        payload = build_job_matches(profile, skills)
        serializer = JobMatchSerializer(payload, many=True)
        return Response(serializer.data)


class AdminCandidatesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "")
        profiles = list(
            Profile.objects.select_related("user")
            .prefetch_related("user__skills")
            .filter(user__role=User.Role.STUDENT, onboarded=True)
        )
        payload = build_admin_candidates(profiles, query=query)
        serializer = AdminCandidateSerializer(payload, many=True)
        return Response(serializer.data)
