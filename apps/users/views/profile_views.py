"""
User profile management views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..serializers import UserDetailSerializer, UserUpdateSerializer


class UserProfileView(APIView):
    """User profile management matching Node.js API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """getUserInfo endpoint"""
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return success_response(serializer.data, 'User info retrieved successfully')

    def post(self, request):
        """modifyInfo endpoint (using POST to match Node.js API)"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            # Return updated user data using detail serializer
            updated_data = UserDetailSerializer(request.user, context={'request': request}).data
            return success_response(updated_data, 'Profile updated successfully')
        return error_response('Profile update failed', serializer.errors)

    def put(self, request):
        """Alternative modifyInfo endpoint (using PUT for REST compliance)"""
        return self.post(request)


class UploadAvatarView(APIView):
    """Avatar upload endpoint matching Node.js API (uploaderImg)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'avatar' not in request.FILES and 'file' not in request.FILES:
            return error_response('No avatar file provided')

        # Support both 'avatar' and 'file' field names for compatibility
        avatar_file = request.FILES.get('avatar') or request.FILES.get('file')
        
        request.user.avatar = avatar_file
        request.user.save()

        return success_response({
            'avatar_url': request.user.avatar.url if request.user.avatar else None,
            'url': request.user.avatar.url if request.user.avatar else None  # Alternative field name
        }, 'Avatar uploaded successfully')

