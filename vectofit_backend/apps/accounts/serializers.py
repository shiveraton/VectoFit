from rest_framework import serializers
from .models import Profile, User
from django import forms
from django.contrib.auth import authenticate
import django.contrib.auth.password_validation as validators

class ProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'user',
            'username',
            'bio',
            'birth_date',
            'profile_picture',
        ]

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