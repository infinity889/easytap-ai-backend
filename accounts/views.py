from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from groq import Groq
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile, Skill, User
from .google_oauth import (
    GoogleOAuthError,
    build_google_authorize_url,
    exchange_code_for_tokens,
    fetch_google_userinfo,
    parse_google_state,
)
from .permissions import IsAdminRole
from .serializers import (
    AdminCandidateSerializer,
    AssistantChatRequestSerializer,
    AssistantChatResponseSerializer,
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
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            callback_url = settings.FRONTEND_GOOGLE_CALLBACK_URL
            params = urlencode({"error": "Google OAuth is not configured on the backend yet."})
            return redirect(f"{callback_url}?{params}")

        role = request.query_params.get("role", User.Role.STUDENT)
        if role not in {User.Role.STUDENT, User.Role.ADMIN}:
            role = User.Role.STUDENT
        next_path = request.query_params.get("next", "")
        return redirect(build_google_authorize_url(role=role, next_path=next_path))


class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        frontend_callback = settings.FRONTEND_GOOGLE_CALLBACK_URL
        error = request.query_params.get("error")
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if error:
            return redirect(f"{frontend_callback}?{urlencode({'error': error})}")
        if not code or not state:
            return redirect(f"{frontend_callback}?{urlencode({'error': 'Missing Google OAuth parameters.'})}")

        try:
            state_payload = parse_google_state(state)
            next_path = state_payload.get("next") or ""
            tokens = exchange_code_for_tokens(code)
            google_access_token = tokens.get("access_token")
            if not google_access_token:
                raise GoogleOAuthError("Google did not return an access token.")

            google_user = fetch_google_userinfo(google_access_token)
            email = (google_user.get("email") or "").strip().lower()
            if not email:
                raise GoogleOAuthError("Google account email is not available.")
            if google_user.get("email_verified") is False:
                raise GoogleOAuthError("Google account email is not verified.")

            full_name = (google_user.get("name") or email.split("@")[0]).strip()
            role = state_payload.get("role") or User.Role.STUDENT
            if role not in {User.Role.STUDENT, User.Role.ADMIN}:
                role = User.Role.STUDENT

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name[:100],
                    "role": role,
                },
            )

            changed_fields: list[str] = []
            if created:
                user.set_unusable_password()
                changed_fields.append("password")
            if not user.full_name and full_name:
                user.full_name = full_name[:100]
                changed_fields.append("full_name")
            if changed_fields:
                user.save(update_fields=changed_fields)

            refresh = CareerTokenObtainPairSerializer.get_token(user)
            params = urlencode(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "next": next_path,
                }
            )
            return redirect(f"{frontend_callback}?{params}")
        except GoogleOAuthError as exc:
            return redirect(f"{frontend_callback}?{urlencode({'error': str(exc)})}")


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


class AssistantChatView(APIView):
    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GROQ_API_KEY:
            return Response(
                {"detail": "Groq API key is not configured on the backend."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        user = request.user
        profile = Profile.objects.filter(user=user).first()
        skills = list(Skill.objects.filter(user=user))
        jobs = build_job_matches(profile, skills)[:4]

        profile_summary = {
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "career_goal": profile.career_goal if profile else "",
            "university": profile.university if profile else "",
            "major": profile.major if profile else "",
            "year": profile.year if profile else None,
            "interests": profile.interests if profile else [],
            "experience": profile.experience if profile else "",
            "skills": [{"name": skill.name, "level": skill.level} for skill in skills],
            "job_matches": jobs,
        }

        system_prompt = (
            "You are EasyTap.ai, an AI career assistant for students. "
            "Give practical, concise, supportive answers. "
            "Use the student's profile and recommended jobs when relevant. "
            "If suggesting vacancies, mention why they fit the student. "
            "Answer in the same language as the user's message when possible."
        )

        user_prompt = (
            "Student context:\n"
            f"{profile_summary}\n\n"
            "User message:\n"
            f"{serializer.validated_data['message']}"
        )

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            reply = completion.choices[0].message.content or "I could not generate a response."
        except Exception:
            return Response(
                {"detail": "Groq request failed. Check GROQ_API_KEY and GROQ_MODEL."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = AssistantChatResponseSerializer(
            {
                "reply": reply,
                "jobs": jobs,
            }
        )
        return Response(response.data)


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
