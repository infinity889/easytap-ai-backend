from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profile, Skill, User, Vacancy


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(format="hex_verbose", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=72)

    class Meta:
        model = User
        fields = ("email", "password", "full_name", "role")

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class CareerTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        credentials = {
            self.username_field: attrs.get(self.username_field),
            "password": attrs.get("password"),
        }
        self.user = authenticate(request=self.context.get("request"), **credentials)
        if self.user is None:
            raise serializers.ValidationError({"detail": "Invalid email or password."})
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="user_id", format="hex_verbose", read_only=True)
    full_name = serializers.CharField(source="user.full_name")

    class Meta:
        model = Profile
        fields = (
            "id",
            "full_name",
            "university",
            "major",
            "year",
            "career_goal",
            "interests",
            "experience",
            "avatar_url",
            "onboarded",
        )

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        full_name = user_data.get("full_name")
        if full_name is not None:
            instance.user.full_name = full_name
            instance.user.save(update_fields=["full_name"])
        return super().update(instance, validated_data)


class SkillSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(format="hex_verbose", read_only=True)

    class Meta:
        model = Skill
        fields = ("id", "name", "level")

    def validate_level(self, value: int) -> int:
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Level must be between 0 and 100.")
        return value


class JobMatchSerializer(serializers.Serializer):
    id = serializers.CharField()
    company = serializers.CharField()
    role = serializers.CharField()
    location = serializers.CharField()
    type = serializers.CharField()
    salary = serializers.CharField()
    match = serializers.IntegerField()
    tags = serializers.ListField(child=serializers.CharField())
    reason = serializers.CharField()
    url = serializers.URLField(required=False, allow_blank=True)
    source = serializers.CharField(required=False, allow_blank=True)
    source_program = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)


class VacancySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(format="hex_verbose", read_only=True)
    type = serializers.CharField(source="employment_type", read_only=True)
    match = serializers.IntegerField(read_only=True)
    reason = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True, default="easytap-db")

    class Meta:
        model = Vacancy
        fields = (
            "id",
            "company",
            "role",
            "location",
            "type",
            "salary",
            "tags",
            "match",
            "reason",
            "url",
            "source",
            "source_program",
            "category",
        )


class AdminCandidateSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    university = serializers.CharField()
    major = serializers.CharField()
    year = serializers.IntegerField()
    top_skill = serializers.CharField()
    match = serializers.IntegerField()


class AssistantChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=4000)


class AssistantChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    jobs = JobMatchSerializer(many=True)


class AssistantChannelChatRequestSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["telegram"])
    external_user_id = serializers.CharField(min_length=1, max_length=64)
    message = serializers.CharField(min_length=1, max_length=4000)


class TelegramLinkStartRequestSerializer(serializers.Serializer):
    tg_user_id = serializers.IntegerField(min_value=1)
    username = serializers.CharField(max_length=64, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class TelegramLinkStartResponseSerializer(serializers.Serializer):
    linked = serializers.BooleanField()
    link_code = serializers.CharField(required=False, allow_blank=True)
    expires_in_seconds = serializers.IntegerField(required=False)
    message = serializers.CharField(required=False, allow_blank=True)


class TelegramLinkConfirmRequestSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=4, max_length=12)


class TelegramLinkStatusSerializer(serializers.Serializer):
    linked = serializers.BooleanField()
    tg_user_id = serializers.IntegerField(required=False)
    tg_username = serializers.CharField(required=False, allow_blank=True)
    tg_full_name = serializers.CharField(required=False, allow_blank=True)
    confirmed_at = serializers.DateTimeField(required=False)
