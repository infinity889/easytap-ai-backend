from urllib.parse import urlencode
import secrets
import string

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from groq import Groq
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import AssistantMessage, FavoriteVacancy, JobApplication, Profile, Skill, TelegramLink, User, Vacancy
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
    AssistantChannelChatRequestSerializer,
    CareerTokenObtainPairSerializer,
    JobMatchSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SkillSerializer,
    FavoriteVacancySerializer,
    JobApplicationSerializer,
    TelegramLinkConfirmRequestSerializer,
    TelegramLinkStartRequestSerializer,
    TelegramLinkStartResponseSerializer,
    TelegramLinkStatusSerializer,
    VacancySerializer,
    UserSerializer,
)
from .services import build_admin_candidates, build_job_matches


def _resolve_history_scope(*, user: User | None, channel: str, external_user_id: str | None) -> dict:
    if user is not None:
        return {"user": user}
    return {"channel": channel, "external_user_id": (external_user_id or "")}


def _get_recent_history(*, user: User | None, channel: str, external_user_id: str | None, limit: int = 12) -> list[dict]:
    scope = _resolve_history_scope(user=user, channel=channel, external_user_id=external_user_id)
    rows = list(AssistantMessage.objects.filter(**scope).order_by("-created_at")[:limit])
    rows.reverse()
    messages: list[dict] = []
    for row in rows:
        role = "assistant" if row.role == AssistantMessage.Role.ASSISTANT else "user"
        messages.append({"role": role, "content": row.content})
    return messages


def _persist_dialog(*, user: User | None, channel: str, external_user_id: str | None, user_text: str, assistant_text: str) -> None:
    AssistantMessage.objects.create(
        user=user,
        channel=channel,
        external_user_id=external_user_id or "",
        role=AssistantMessage.Role.USER,
        content=user_text,
    )
    AssistantMessage.objects.create(
        user=user,
        channel=channel,
        external_user_id=external_user_id or "",
        role=AssistantMessage.Role.ASSISTANT,
        content=assistant_text,
    )


def _run_assistant(*, user: User | None, user_message: str, channel: str, external_user_id: str | None = None) -> dict:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("missing_groq_key")

    profile = Profile.objects.filter(user=user).first() if user else None
    skills = list(Skill.objects.filter(user=user)) if user else []
    jobs = build_job_matches(profile, skills, query=user_message)[:6]

    profile_summary = {
        "full_name": user.full_name if user else "",
        "email": user.email if user else "",
        "role": user.role if user else "guest",
        "career_goal": profile.career_goal if profile else "",
        "university": profile.university if profile else "",
        "major": profile.major if profile else "",
        "year": profile.year if profile else None,
        "interests": profile.interests if profile else [],
        "experience": profile.experience if profile else "",
        "skills": [{"name": skill.name, "level": skill.level} for skill in skills],
        "job_matches": jobs,
    }
    history = _get_recent_history(user=user, channel=channel, external_user_id=external_user_id, limit=12)

    system_prompt = (
        "You are EasyTap.ai, an AI career assistant for students. "
        "Give practical, concise, supportive answers focused on getting hired. "
        "No fluff, no long intros, no generic theory. "
        "Use short bullet points and concrete actions. "
        "Use the student's profile and vacancies context from the internal EasyTap database. "
        "Provide concrete steps for resume, application, and interview preparation. "
        "Do not invent data outside the provided vacancies list. "
        "Answer in the same language as the user's message when possible."
    )
    context_prompt = (
        "Student context:\n"
        f"{profile_summary}\n\n"
        "Conversation history:\n"
        f"{history}\n\n"
        "User message:\n"
        f"{user_message}\n\n"
        "Required output:\n"
        "1) Best 2-3 vacancies and why they fit (one short line each).\n"
        "2) Practical 48-hour application plan (max 5 bullets).\n"
        "3) Interview prep tips specific to these roles (max 4 bullets).\n"
        "Keep total response under 1400 characters."
    )

    client = Groq(api_key=settings.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_prompt},
        ],
    )
    reply = completion.choices[0].message.content or "I could not generate a response."
    _persist_dialog(
        user=user,
        channel=channel,
        external_user_id=external_user_id,
        user_text=user_message,
        assistant_text=reply,
    )
    return {"reply": reply, "jobs": jobs}


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


class VacancyCatalogView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        category = request.query_params.get("category", "").strip()
        employment_type = request.query_params.get("type", "").strip()
        location = request.query_params.get("location", "").strip()
        limit_raw = request.query_params.get("limit", "120")
        try:
            limit = max(1, min(300, int(limit_raw)))
        except ValueError:
            limit = 120

        items = Vacancy.objects.filter(is_active=True).only(
            "id",
            "company",
            "role",
            "location",
            "employment_type",
            "salary",
            "tags",
            "description",
            "url",
            "source_program",
            "program_code",
            "program_level",
            "category",
            "created_at",
            "updated_at",
        )

        if query:
            items = items.filter(
                Q(role__icontains=query)
                | Q(company__icontains=query)
                | Q(location__icontains=query)
                | Q(source_program__icontains=query)
                | Q(description__icontains=query)
            )
        if category:
            items = items.filter(category__iexact=category)
        if employment_type:
            items = items.filter(employment_type__iexact=employment_type)
        if location:
            items = items.filter(location__iexact=location)

        items = items.order_by("category", "role")[:limit]
        serializer = VacancySerializer(items, many=True)
        return Response(serializer.data)


class VacancyDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, vacancy_id):
        vacancy = Vacancy.objects.filter(id=vacancy_id, is_active=True).first()
        if vacancy is None:
            return Response({"detail": "Vacancy not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacancySerializer(vacancy)
        return Response(serializer.data)


class AssistantChatView(APIView):
    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = _run_assistant(
                user=request.user,
                user_message=serializer.validated_data["message"],
                channel=AssistantMessage.Channel.WEB,
                external_user_id=None,
            )
        except RuntimeError:
            return Response(
                {"detail": "Groq API key is not configured on the backend."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            return Response(
                {"detail": "Groq request failed. Check GROQ_API_KEY and GROQ_MODEL."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = AssistantChatResponseSerializer(payload)
        return Response(response.data)


class AssistantChannelChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AssistantChannelChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = None
        if data["channel"] == "telegram":
            link = TelegramLink.objects.filter(tg_user_id=int(data["external_user_id"]), user__isnull=False).first()
            if link:
                user = link.user

        try:
            payload = _run_assistant(
                user=user,
                user_message=data["message"],
                channel=AssistantMessage.Channel.TELEGRAM,
                external_user_id=str(data["external_user_id"]),
            )
        except RuntimeError:
            return Response(
                {"detail": "Groq API key is not configured on the backend."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            return Response(
                {"detail": "Groq request failed. Check GROQ_API_KEY and GROQ_MODEL."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = AssistantChatResponseSerializer(payload)
        return Response(response.data)


class AdminCandidatesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            min_match = int(request.query_params.get("min_match", "0"))
        except ValueError:
            min_match = 0
        year_raw = request.query_params.get("year")
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None
        profiles = list(
            Profile.objects.select_related("user")
            .prefetch_related("user__skills")
            .filter(user__role=User.Role.STUDENT, onboarded=True)
        )
        payload = build_admin_candidates(profiles, query=query, min_match=min_match, year=year)
        serializer = AdminCandidateSerializer(payload, many=True)
        return Response(serializer.data)


class TelegramLinkStartView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramLinkStartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        link, _ = TelegramLink.objects.get_or_create(tg_user_id=data["tg_user_id"])
        link.tg_username = data.get("username", "") or ""
        link.tg_full_name = data.get("full_name", "") or ""

        if link.user_id:
            response = TelegramLinkStartResponseSerializer(
                {
                    "linked": True,
                    "message": "Telegram already linked to a website account.",
                }
            )
            return Response(response.data)

        if not link.is_code_active:
            alphabet = string.ascii_uppercase + string.digits
            link.link_code = "".join(secrets.choice(alphabet) for _ in range(6))
            link.code_expires_at = TelegramLink.default_expiry()
            link.confirmed_at = None
            link.save(
                update_fields=[
                    "tg_username",
                    "tg_full_name",
                    "link_code",
                    "code_expires_at",
                    "confirmed_at",
                    "updated_at",
                ]
            )
        else:
            link.save(update_fields=["tg_username", "tg_full_name", "updated_at"])

        expires_in = int((link.code_expires_at - timezone.now()).total_seconds()) if link.code_expires_at else 0
        response = TelegramLinkStartResponseSerializer(
            {"linked": False, "link_code": link.link_code, "expires_in_seconds": max(0, expires_in)}
        )
        return Response(response.data)


class TelegramLinkConfirmView(APIView):
    def post(self, request):
        serializer = TelegramLinkConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"].strip().upper()

        link = TelegramLink.objects.filter(link_code=code).first()
        if link is None or not link.is_code_active:
            return Response({"detail": "Invalid or expired Telegram code."}, status=status.HTTP_400_BAD_REQUEST)

        if link.user_id and link.user_id != request.user.id:
            return Response({"detail": "This Telegram account is already linked to another user."}, status=409)

        existing_for_user = TelegramLink.objects.filter(user=request.user).exclude(pk=link.pk).first()
        if existing_for_user:
            existing_for_user.user = None
            existing_for_user.save(update_fields=["user", "updated_at"])

        link.user = request.user
        link.confirmed_at = timezone.now()
        link.link_code = ""
        link.code_expires_at = None
        link.save(update_fields=["user", "confirmed_at", "link_code", "code_expires_at", "updated_at"])

        # Merge previous Telegram-only dialog history into this website user.
        # This makes assistant context seamless after account linking.
        AssistantMessage.objects.filter(
            user__isnull=True,
            channel=AssistantMessage.Channel.TELEGRAM,
            external_user_id=str(link.tg_user_id),
        ).update(user=request.user)

        return Response({"linked": True})


class TelegramLinkStatusView(APIView):
    def get(self, request):
        link = TelegramLink.objects.filter(user=request.user).first()
        if not link:
            response = TelegramLinkStatusSerializer({"linked": False})
            return Response(response.data)

        response = TelegramLinkStatusSerializer(
            {
                "linked": True,
                "tg_user_id": link.tg_user_id,
                "tg_username": link.tg_username,
                "tg_full_name": link.tg_full_name,
                "confirmed_at": link.confirmed_at,
            }
        )
        return Response(response.data)


class TelegramLinkUnlinkView(APIView):
    def post(self, request):
        link = TelegramLink.objects.filter(user=request.user).first()
        if not link:
            return Response({"linked": False})

        link.user = None
        link.confirmed_at = None
        link.link_code = ""
        link.code_expires_at = None
        link.save(update_fields=["user", "confirmed_at", "link_code", "code_expires_at", "updated_at"])
        return Response({"linked": False})


class FavoriteVacancyListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoriteVacancySerializer

    def get_queryset(self):
        return FavoriteVacancy.objects.filter(user=self.request.user).select_related("vacancy")

    def create(self, request, *args, **kwargs):
        vacancy_id = request.data.get("vacancy_id")
        vacancy = Vacancy.objects.filter(id=vacancy_id, is_active=True).first()
        if vacancy is None:
            return Response({"detail": "Vacancy not found."}, status=status.HTTP_404_NOT_FOUND)
        favorite, _ = FavoriteVacancy.objects.get_or_create(user=request.user, vacancy=vacancy)
        serializer = self.get_serializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FavoriteVacancyDeleteView(APIView):
    def delete(self, request, vacancy_id):
        favorite = FavoriteVacancy.objects.filter(user=request.user, vacancy_id=vacancy_id).first()
        if not favorite:
            return Response(status=status.HTTP_204_NO_CONTENT)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related("vacancy")

    def create(self, request, *args, **kwargs):
        vacancy_id = request.data.get("vacancy_id")
        vacancy = Vacancy.objects.filter(id=vacancy_id, is_active=True).first()
        if vacancy is None:
            return Response({"detail": "Vacancy not found."}, status=status.HTTP_404_NOT_FOUND)
        status_value = request.data.get("status") or JobApplication.Status.PLANNED
        note = request.data.get("note", "")
        application, _ = JobApplication.objects.update_or_create(
            user=request.user,
            vacancy=vacancy,
            defaults={"status": status_value, "note": note},
        )
        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related("vacancy")


class TelegramFavoritesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tg_user_id_raw = request.query_params.get("tg_user_id", "").strip()
        if not tg_user_id_raw.isdigit():
            return Response({"detail": "tg_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        link = TelegramLink.objects.filter(tg_user_id=int(tg_user_id_raw), user__isnull=False).first()
        if link is None:
            return Response({"linked": False, "items": []})

        favorites = FavoriteVacancy.objects.filter(user=link.user).select_related("vacancy")[:10]
        items = []
        for favorite in favorites:
            vacancy = favorite.vacancy
            items.append(
                {
                    "vacancy_id": str(vacancy.id),
                    "role": vacancy.role,
                    "company": vacancy.company,
                    "location": vacancy.location,
                    "salary": vacancy.salary,
                    "url": vacancy.url,
                    "saved_at": favorite.created_at,
                }
            )
        return Response({"linked": True, "items": items})


class TelegramApplicationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tg_user_id_raw = request.query_params.get("tg_user_id", "").strip()
        if not tg_user_id_raw.isdigit():
            return Response({"detail": "tg_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        link = TelegramLink.objects.filter(tg_user_id=int(tg_user_id_raw), user__isnull=False).first()
        if link is None:
            return Response({"linked": False, "items": []})

        applications = JobApplication.objects.filter(user=link.user).select_related("vacancy")[:10]
        items = []
        for application in applications:
            vacancy = application.vacancy
            items.append(
                {
                    "application_id": application.id,
                    "status": application.status,
                    "note": application.note,
                    "updated_at": application.updated_at,
                    "vacancy_id": str(vacancy.id),
                    "role": vacancy.role,
                    "company": vacancy.company,
                    "location": vacancy.location,
                    "salary": vacancy.salary,
                    "url": vacancy.url,
                }
            )
        return Response({"linked": True, "items": items})
