"""
Admin user management views.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q

from apps.common.utils import success_response, error_response
from ..models import User
from ..serializers import UserListSerializer


class AdminGetUserListView(APIView):
    """Get user list for admin - matches /api/admin/getUserList"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get query parameters
            keyword = request.GET.get('keyword', '')
            user_type = request.GET.get('type', '')
            page_index = int(request.GET.get('pageIndex', 0))
            page_size = int(request.GET.get('pageSize', 20))
            
            # Build query
            users = User.objects.all()
            
            # Apply keyword search (user ID, phone, username)
            if keyword:
                users = users.filter(
                    Q(id__icontains=keyword) |
                    Q(phone__icontains=keyword) |
                    Q(username__icontains=keyword) |
                    Q(first_name__icontains=keyword)
                )
            
            # Apply type filter if provided
            # type: 0=normal, 1=staff, etc. (can be extended)
            if user_type is not None and user_type != '':
                try:
                    type_value = int(user_type)
                    if type_value == 1:
                        users = users.filter(is_staff=True)
                    elif type_value == 0:
                        users = users.filter(is_staff=False)
                except ValueError:
                    pass
            
            # Order by creation time descending
            users = users.order_by('-created_at')
            
            # Apply pagination
            total = users.count()
            start_index = page_index * page_size
            end_index = start_index + page_size
            page_users = users[start_index:end_index]
            
            # Serialize user data
            serializer = UserListSerializer(page_users, many=True, context={'request': request})
            
            # Transform to match frontend expected format
            user_list = []
            for user_data in serializer.data:
                user_obj = User.objects.get(id=user_data['id'])
                user_list.append({
                    'uid': user_data['id'],
                    'nickName': user_obj.first_name or user_obj.username or '微信用户',
                    'avatar': user_data.get('avatar_url') or '',
                    'phone': user_obj.phone or '',
                    'userRemark': '',  # Not in current model, can be added later
                    'AccStatus': 0 if user_obj.is_active else 1,  # 0=正常, 1=异常
                    'lastLoginTime': user_obj.last_login.isoformat() if user_obj.last_login else '',
                })
            
            # Return in format matching Node.js API (array format)
            return success_response(user_list, '用户列表获取成功')
            
        except Exception as e:
            return error_response(f'获取用户列表失败: {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
