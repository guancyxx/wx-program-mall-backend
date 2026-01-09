"""
Custom authentication classes for handling edge cases
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class SafeJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that gracefully handles user not found cases.
    
    When a token contains a user_id that doesn't exist (e.g., user was deleted),
    instead of raising an exception, this class returns None, allowing the
    request to proceed as unauthenticated.
    """
    
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        Returns None if user not found instead of raising an exception.
        """
        try:
            user_id = validated_token.get(api_settings.USER_ID_CLAIM)
            if user_id is None:
                return None
            
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            return user
        except User.DoesNotExist:
            logger.warning(f'JWT token contains invalid user_id: {user_id}')
            # Return None instead of raising exception
            # This allows the request to proceed as unauthenticated
            return None
        except (TypeError, ValueError, KeyError) as e:
            logger.error(f'Invalid token payload: {str(e)}')
            raise InvalidToken(f'Token contained invalid user identification: {str(e)}')
        except Exception as e:
            logger.error(f'Unexpected error during user lookup: {str(e)}')
            raise AuthenticationFailed(f'User lookup failed: {str(e)}')

