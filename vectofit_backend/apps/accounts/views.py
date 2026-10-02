from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Profile
from .serializers import ProfileSerializer, UserSerializer, RegisterSerializer, LoginSerializer 

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

class CurrentUserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(
            {
                'message': 'User registered successfully.'
            },
            status=status.HTTP_201_CREATED
        )

        print(f"DEBUG: {serializer.errors}")

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        print(f"DEBUG: Request data received: {request.data}")
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'token': token.key
                },
                status=status.HTTP_200_OK
            )

        print(f"DEBUG: Serializer errors: {serializer.errors}")

        return Response(
            serializer.errors,
            status=status.HTTP_401_UNAUTHORIZED
        )