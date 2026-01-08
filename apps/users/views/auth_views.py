"""
User authentication views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.core.cache import cache

from apps.common.utils import success_response, error_response
from ..models import User
from ..serializers import UserDetailSerializer, UserRegistrationSerializer


class RegisterView(APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            # Cache user data for performance
            user_data = UserDetailSerializer(user, context={'request': request}).data
            cache.set(f'user:{user.id}', user_data, 300)  # 5 minutes
            
            return success_response({
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user': user_data
            }, 'Registration successful')
        return error_response('Registration failed', serializer.errors)


class PasswordLoginView(APIView):
    """Password-based login endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')
        username = request.data.get('username')
        email = request.data.get('email')

        if not password:
            return error_response('Password is required')

        # Support login with phone, username, or email
        user = None
        if phone:
            try:
                user = User.objects.select_related('membership_status__tier').get(phone=phone)
            except User.DoesNotExist:
                pass
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        elif email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        else:
            return error_response('Phone, username, or email is required')

        if not user:
            return error_response('Invalid credentials')

        # Check password using Django's built-in password checking (supports bcrypt)
        if user.password and check_password(password, user.password):
            refresh = RefreshToken.for_user(user)
            user.save()  # Update last_login
            return success_response({
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserDetailSerializer(user, context={'request': request}).data
            }, 'Login successful')
        else:
            return error_response('Invalid credentials')


class WeChatLoginView(APIView):
    """WeChat OAuth login endpoint"""
    permission_classes = [AllowAny]

    def _download_avatar(self, avatar_url, user):
        """Download and save avatar from WeChat"""
        import requests
        from django.core.files.base import ContentFile
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Download avatar image
            response = requests.get(avatar_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type for avatar: {content_type}")
                return False
            
            # Get file extension from URL or content type
            ext = os.path.splitext(avatar_url.split('?')[0])[1]  # Remove query params
            if not ext:
                # Try to determine from content type
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'gif' in content_type:
                    ext = '.gif'
                else:
                    ext = '.jpg'  # Default to jpg
            
            filename = f'avatars/{user.id}_wechat{ext}'
            
            # Delete old avatar if exists
            if user.avatar:
                try:
                    user.avatar.delete(save=False)
                except Exception:
                    pass
            
            # Save to user's avatar field
            user.avatar.save(
                filename,
                ContentFile(response.content),
                save=False
            )
            
            logger.info(f"Successfully downloaded and saved avatar for user {user.id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to download avatar for user {user.id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to save avatar for user {user.id}: {str(e)}")
            return False

    def post(self, request):
        from apps.common.wechat import WeChatAPI
        
        code = request.data.get('code')
        phone_code = request.data.get('phoneCode')
        # User info from WeChat getUserProfile API
        nickname = request.data.get('nickName')
        avatar_url = request.data.get('avatarUrl')

        if not code:
            return error_response('WeChat code is required')

        wechat_api = WeChatAPI()
        
        # Get session info from WeChat
        session_info, error = wechat_api.code2session(code)
        if error:
            return error_response(f'WeChat authentication failed: {error}')

        openid = session_info['openid']
        session_key = session_info['session_key']
        is_new_user = False
        wechat_phone = None

        # Try to find existing user
        try:
            user = User.objects.get(wechat_openid=openid)
            user.wechat_session_key = session_key
            user.save(update_fields=['wechat_session_key'])
        except User.DoesNotExist:
            is_new_user = True

        # Get phone number if phone_code is provided
        if phone_code:
            phone_info, phone_error = wechat_api.get_phone_number(phone_code, session_key)
            if phone_info and phone_info.get('phone_number'):
                wechat_phone = phone_info['phone_number']

        # Create or update user
        if is_new_user:
            # Use WeChat nickname as username if available, otherwise use openid
            username = nickname or f"wx_{openid[:8]}"
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create(
                username=username,
                first_name=nickname or '',
                phone=wechat_phone,
                wechat_openid=openid,
                wechat_session_key=session_key
            )
            
            # Download and save avatar after user is created
            if avatar_url:
                if self._download_avatar(avatar_url, user):
                    # Force save to update avatar field in database
                    user.save(update_fields=['avatar'])
                    # Refresh from database to get updated avatar URL
                    user.refresh_from_db()
        else:
            # Update existing user with WeChat info
            update_fields = ['wechat_session_key']
            
            # Update nickname if provided and not set
            if nickname and (not user.first_name or user.first_name == ''):
                user.first_name = nickname
                update_fields.append('first_name')
            
            # Update username if it's a default wx_ username and we have nickname
            if nickname and user.username.startswith('wx_'):
                new_username = nickname
                base_username = new_username
                counter = 1
                while User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                    new_username = f"{base_username}_{counter}"
                    counter += 1
                user.username = new_username
                update_fields.append('username')
            
            # Update phone if provided and not set
            if wechat_phone and not user.phone:
                user.phone = wechat_phone
                update_fields.append('phone')
            
            # Download and save avatar if provided and not set
            if avatar_url and not user.avatar:
                if self._download_avatar(avatar_url, user):
                    update_fields.append('avatar')
            
            if update_fields:
                user.save(update_fields=update_fields)
                # Refresh from database to get updated avatar URL if avatar was updated
                if 'avatar' in update_fields:
                    user.refresh_from_db()

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        
        return success_response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserDetailSerializer(user, context={'request': request}).data
        }, 'WeChat login successful')

