"""
User views module.

All views are exported from this module to maintain backward compatibility.
"""
from .auth_views import RegisterView, PasswordLoginView, WeChatLoginView
from .profile_views import UserProfileView, UploadAvatarView
from .address_views import AddressViewSet
from .admin_views import AdminGetUserListView

__all__ = [
    'RegisterView',
    'PasswordLoginView',
    'WeChatLoginView',
    'UserProfileView',
    'UploadAvatarView',
    'AddressViewSet',
    'AdminGetUserListView',
]

