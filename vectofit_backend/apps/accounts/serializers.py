from typing import ClassVar

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import Profile, User
from .roles import grant_annotator


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    height_cm = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False,
    )

    weight_kg = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False,
    )

    bmi = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields: ClassVar[list] = [
            "user",
            "username",
            "bio",
            "birth_date",
            "profile_picture",
            "height_cm",
            "weight_kg",
            "bmi",
        ]

        read_only_fields: ClassVar[list] = ["user", "username", "bmi"]

    def validate_height_cm(self, value):
        if value is not None and not 50 <= float(value) <= 250:
            raise serializers.ValidationError("Height must be between 50 and 250 cm.")
        return value

    def validate_weight_kg(self, value):
        if value is not None and not 20 <= float(value) <= 500:
            raise serializers.ValidationError("Weight must be between 20 and 500 kg.")
        return value

    def get_bmi(self, obj):
        if obj.height_cm or not obj.weight_kg:
            return None

        height_m = float(obj.height_cm) / 100
        weight_kg = float(obj.weight_kg)

        if height_m <= 0:
            return None

        bmi = float(weight_kg) / (height_m**2)
        return round(bmi, 1)


class UserSerializer(serializers.ModelSerializer):
    is_annotator = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields: ClassVar[list] = [
            "id",
            "username",
            "email",
            "is_staff",
            "is_annotator",
            "role",
        ]
        read_only_fields: ClassVar[list] = ["id", "is_staff", "is_annotator", "role"]

    def get_is_annotator(self, obj):
        from .roles import is_annotator

        return is_annotator(obj)

    def get_role(self, obj):
        if obj.is_staff:
            return "admin"
        return "annotator" if self.get_is_annotator(obj) else "user"


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"}, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    invite_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        default="",
    )

    class Meta:
        model = User
        fields: ClassVar[list] = [
            "username",
            "email",
            "password",
            "confirm_password",
            "invite_code",
        ]

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError("Enter a username.")
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("That username is already taken.")
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with that email already exists."
            )
        return email

    def validate(self, attrs):
        if not getattr(settings, "ANNOTATOR_SELF_REGISTRATION", True):
            raise serializers.ValidationError(
                {"detail": "Public annotator sign-up is disabled."}
            )

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        required_code = getattr(settings, "ANNOTATOR_INVITE_CODE", "")
        if required_code:
            supplied = (attrs.get("invite_code") or "").strip()
            if supplied != required_code:
                raise serializers.ValidationError(
                    {"invite_code": "That invite code is not valid."}
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        validated_data.pop("invite_code", None)

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        grant_annotator(user)

        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        user = User.objects.filter(username=identifier).first()
        if not user:
            user = User.objects.filter(email=identifier).first()

        if not user:
            raise serializers.ValidationError("Invalid username or password.")

        authenticated_user = authenticate(username=user.username, password=password)

        if not authenticated_user:
            raise serializers.ValidationError("Invalid username or password.")

        attrs["user"] = authenticated_user
        return attrs
