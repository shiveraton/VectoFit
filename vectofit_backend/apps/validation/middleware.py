from django.http import JsonResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.roles import is_validator


class ValidatorIsolationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if request.META.get("HTTP_AUTHORIZATION", "").lower().startswith("token "):
            try:
                authenticated = TokenAuthentication().authenticate(request)
                if authenticated:
                    user = authenticated[0]
            except AuthenticationFailed:
                pass
        if is_validator(user):
            validation_path = request.path.startswith(("/api/validation/", "/validation/"))
            account_read = request.method in {"GET", "HEAD", "OPTIONS"} and request.path.startswith("/api/accounts/")
            if not validation_path and not account_read:
                return JsonResponse({"detail": "Validator accounts may only access blinded validation."}, status=403)
        return self.get_response(request)
