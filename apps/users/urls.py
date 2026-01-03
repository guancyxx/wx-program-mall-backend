from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'addresses', views.AddressViewSet, basename='address')

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.WeChatLoginView.as_view(), name='wechat-login'),
    path('passwordLogin/', views.PasswordLoginView.as_view(), name='password-login'),
    path('getUserInfo/', views.UserProfileView.as_view(), name='get-user-info'),
    path('modifyInfo/', views.UserProfileView.as_view(), name='modify-info'),
    path('uploaderImg/', views.UploadAvatarView.as_view(), name='upload-avatar'),
    path('addAddress/', views.AddAddressView.as_view(), name='add-address'),
    path('deleteAddress/', views.DeleteAddressView.as_view(), name='delete-address'),
    path('getAddressList/', views.AddressListView.as_view(), name='get-address-list'),
    path('', include(router.urls)),
]