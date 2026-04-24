import uuid
from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError("The email field must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.STUDENT)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    university = models.CharField(max_length=150, blank=True)
    major = models.CharField(max_length=150, blank=True)
    year = models.PositiveSmallIntegerField(default=1)
    career_goal = models.CharField(max_length=200, blank=True)
    interests = models.JSONField(default=list, blank=True)
    experience = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True, null=True)
    onboarded = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=60)
    level = models.PositiveSmallIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_skill_per_user"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.level})"


class TelegramLink(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="telegram_link", null=True, blank=True
    )
    tg_user_id = models.BigIntegerField(unique=True)
    tg_username = models.CharField(max_length=64, blank=True)
    tg_full_name = models.CharField(max_length=120, blank=True)
    link_code = models.CharField(max_length=12, blank=True, db_index=True)
    code_expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_code_active(self) -> bool:
        if not self.link_code or not self.code_expires_at:
            return False
        return self.code_expires_at > timezone.now()

    @staticmethod
    def default_expiry():
        return timezone.now() + timedelta(minutes=30)

    def __str__(self) -> str:
        status = "linked" if self.user_id else "pending"
        return f"TelegramLink<{self.tg_user_id}>:{status}"


class AssistantMessage(models.Model):
    class Channel(models.TextChoices):
        WEB = "web", "Web"
        TELEGRAM = "telegram", "Telegram"

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="assistant_messages", null=True, blank=True
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    external_user_id = models.CharField(max_length=64, blank=True, db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        owner = self.user_id or self.external_user_id or "anon"
        return f"AssistantMessage<{self.channel}:{owner}:{self.role}>"
