"""
User profile management views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..serializers import UserDetailSerializer, UserUpdateSerializer, UserInfoSerializer


class UserProfileView(APIView):
    """User profile management matching Node.js API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """getUserInfo endpoint"""
        serializer = UserInfoSerializer(request.user, context={'request': request})
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
    """
    Avatar upload endpoint matching Node.js API (uploaderImg).
    Note: This endpoint is deprecated. Avatar should be updated via modifyInfo endpoint with URL string.
    Kept for backward compatibility but returns error.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return error_response(
            'This endpoint is deprecated. Please use modifyInfo endpoint to update avatar with URL string.',
            status_code=410  # Gone
        )

