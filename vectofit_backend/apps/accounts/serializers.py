from rest_framework import serializers
from .models import Profile, User
from django import forms
from django.contrib.auth import authenticate
import django.contrib.auth.password_validation as validators

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    height_cm = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False
    )

    weight_kg = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        coerce_to_string=False
    )

    bmi = serializers.SerializerMethodField()
    
    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'bio',
            'birth_date',
            'profile_picture',
            'height_cm',
            'weight_kg',
            'bmi'
        ]

        read_only_fields = [
            'user',
            'username',
            'bmi'
        ]

    def validate_height_cm(self, value):
        if value is not None and not 50 <= float(value) <= 250:
            raise serializers.ValidationError(
                "Height must be between 50 and 250 cm."
            )
        return value

    def validate_weight_kg(self, value):
        if value is not None and not 20 <= float(value) <= 500:
            raise serializers.ValidationError(
                "Weight must be between 20 and 500 kg."
            )
        return value

    def get_bmi(self, obj):
        if obj.height_cm or not obj.weight_kg:
            return None

        height_m = float(obj.height_cm) / 100
        weight_kg = float(obj.weight_kg)

        if height_m <= 0:
            return None

        bmi = float(weight_kg) / (height_m ** 2)
        return round(bmi, 1)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):

    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'confirm_password',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        return user

class LoginSerializer(serializers.Serializer):

    identifier = serializers.CharField()
    password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        print(f"DEBUG: Validating identifier: {identifier}")

        user = User.objects.filter(username=identifier).first()
        if not user:
            user = User.objects.filter(email=identifier).first()

        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        authenticated_user = authenticate(
            username=user.username,
            password=password
        )

        if not authenticated_user:
            print(f"DEBUG: Password incorrect for user: {user.username}")
            raise serializers.ValidationError(
                'Invalid username or password.'
            )

        attrs['user'] = authenticated_user
        return attrs