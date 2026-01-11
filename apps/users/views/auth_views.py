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
        """
        Save avatar URL from WeChat to user's avatar field.
        Note: Avatar is now stored as URL string in cloud storage, not as file.
        """
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            if not avatar_url:
                logger.warning(f"No avatar URL provided for user {user.id}")
                return False
            
            # Save avatar URL directly to user's avatar field (now URLField)
            user.avatar = avatar_url
            user.save(update_fields=['avatar'])
            
            logger.info(f"Successfully saved avatar URL for user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save avatar for user {user.id}: {str(e)}")
            return False

    def post(self, request):
        from apps.common.wechat import WeChatAPI
        import logging
        
        logger = logging.getLogger(__name__)
        
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
            logger.error(f'WeChat code2session failed: {error}')
            return error_response(f'WeChat authentication failed: {error}')

        openid = session_info.get('openid')
        session_key = session_info.get('session_key')
        
        if not openid:
            logger.error('WeChat code2session returned empty openid')
            return error_response('Failed to get WeChat openid, please try again')
        
        if not session_key:
            logger.error('WeChat code2session returned empty session_key')
            return error_response('Failed to get WeChat session_key, please try again')
        
        is_new_user = False
        wechat_phone = None

        # Try to find existing user by wechat_openid
        try:
            user = User.objects.get(wechat_openid=openid)
            logger.info(f'Found existing user: {user.id} (openid: {openid})')
            user.wechat_session_key = session_key
            user.save(update_fields=['wechat_session_key'])
        except User.DoesNotExist:
            is_new_user = True
            logger.info(f'User not found for openid: {openid}, will create new user')

        # Get phone number if phone_code is provided
        if phone_code:
            phone_info, phone_error = wechat_api.get_phone_number(phone_code, session_key)
            if phone_info and phone_info.get('phone_number'):
                wechat_phone = phone_info['phone_number']

        # Create or update user
        if is_new_user:
            try:
                # Use WeChat nickname as username if available, otherwise use openid
                username = nickname or f"wx_{openid[:8]}"
                # Ensure username is unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Create new user
                user = User.objects.create(
                    username=username,
                    first_name=nickname or '',
                    phone=wechat_phone,
                    wechat_openid=openid,
                    wechat_session_key=session_key
                )
                logger.info(f'Created new user: {user.id} (username: {username}, openid: {openid})')
                
                # Save avatar URL after user is created
                if avatar_url:
                    self._download_avatar(avatar_url, user)
            except Exception as e:
                logger.error(f'Failed to create user for openid {openid}: {str(e)}', exc_info=True)
                return error_response(f'Failed to create user: {str(e)}')
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
            
            # Save avatar URL if provided and not set
            if avatar_url and not user.avatar:
                self._download_avatar(avatar_url, user)
            
            if update_fields:
                user.save(update_fields=update_fields)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        
        return success_response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserDetailSerializer(user, context={'request': request}).data
        }, 'WeChat login successful')

