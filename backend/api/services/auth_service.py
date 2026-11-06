"""
Servicio de Aplicación para Autenticación y Gestión de Tokens de Administradores.
"""

from typing import Any, Dict
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token


class AuthValidationError(ValueError):
    pass


class AuthCredentialsError(PermissionError):
    pass


class AuthForbiddenError(PermissionError):
    pass


class AdminAuthService:
    @classmethod
    def login_superuser(cls, request, username: str, password: str) -> Dict[str, Any]:
        clean_username = (username or '').strip()
        clean_password = password or ''

        if not clean_username or not clean_password:
            raise AuthValidationError('Por favor ingresa usuario y contraseña.')

        user = authenticate(request, username=clean_username, password=clean_password)
        if user is None:
            raise AuthCredentialsError('Usuario o contraseña incorrectos.')

        if not user.is_superuser:
            raise AuthForbiddenError('Acceso restringido únicamente a administradores.')

        token, _ = Token.objects.get_or_create(user=user)
        return {
            'token': token.key,
            'user': {
                'username': user.username,
                'is_superuser': user.is_superuser,
            },
            'message': f'¡Bienvenido de nuevo, {user.username}!',
        }

    @classmethod
    def logout_user(cls, user) -> Dict[str, str]:
        if hasattr(user, 'auth_token'):
            user.auth_token.delete()
        return {'message': 'Has cerrado sesión exitosamente.'}

    @classmethod
    def get_user_profile(cls, user) -> Dict[str, Any]:
        return {
            'user': {
                'username': user.username,
                'is_superuser': user.is_superuser,
            }
        }
