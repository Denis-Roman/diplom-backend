import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from school.models import User
from school.models import GroupStudent


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

        user_status = str(getattr(user, 'status', '') or '').strip().lower()
        if not bool(getattr(user, 'is_active', True)) or user_status == 'inactive':
            raise AuthenticationFailed('Account is inactive')

        # If legacy data has membership in GroupStudents but Users.group is null,
        # patch it for the current request to keep API filters working.
        if getattr(user, 'role', None) == 'student' and getattr(user, 'group_id', None) is None:
            membership = GroupStudent.objects.select_related('group').filter(student=user).first()
            if membership and membership.group_id:
                user.group = membership.group
                user.group_id = membership.group_id

        return (user, token)
