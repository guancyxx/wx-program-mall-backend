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

    def post(self, request):
        from apps.common.wechat import WeChatAPI
        
        code = request.data.get('code')
        phone_code = request.data.get('phoneCode')
        encrypted_data = request.data.get('encryptedData')
        iv = request.data.get('iv')

        if not code:
            return error_response('WeChat code is required')

        wechat_api = WeChatAPI()
        
        # Get session info from WeChat
        session_info, error = wechat_api.code2session(code)
        if error:
            return error_response(f'WeChat authentication failed: {error}')

        openid = session_info['openid']
        session_key = session_info['session_key']

        # Try to find existing user
        try:
            user = User.objects.get(wechat_openid=openid)
            # Update session key
            user.wechat_session_key = session_key
            user.save()
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create(
                username=f"wx_{openid[:8]}",
                wechat_openid=openid,
                wechat_session_key=session_key
            )

        # Handle phone number if phone_code is provided
        if phone_code:
            phone_info, phone_error = wechat_api.get_phone_number(phone_code, session_key)
            if phone_info and phone_info.get('phone_number'):
                user.phone = phone_info['phone_number']
                user.save()

        # Handle encrypted user data if provided
        if encrypted_data and iv:
            user_info, decrypt_error = wechat_api.decrypt_data(encrypted_data, iv, session_key)
            if user_info:
                # Update user info from WeChat
                if user_info.get('nickName') and not user.first_name:
                    user.first_name = user_info['nickName']
                if user_info.get('avatarUrl') and not user.avatar:
                    # TODO: Download and save avatar from WeChat
                    pass
                user.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        
        return success_response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserDetailSerializer(user, context={'request': request}).data
        }, 'WeChat login successful')

