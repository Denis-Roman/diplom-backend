import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from school.models import User


class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication that reads token from 'auth-token' cookie
    or 'Authorization: Bearer <token>' header.
    """

    def authenticate(self, request):
        token = request.COOKIES.get('auth-token')

        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        if not token:
            return None

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')

        try:
            user = User.objects.get(pk=payload['userId'])
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

        return (user, token)
