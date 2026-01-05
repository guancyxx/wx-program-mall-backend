from django.urls import path
from . import views

urlpatterns = [
    # Order management endpoints matching Node.js API
    path('createOrder', views.CreateOrderView.as_view(), name='create-order'),
    path('getMyOrder', views.GetMyOrderView.as_view(), name='get-my-order'),
    path('getOrderDetail', views.GetOrderDetailView.as_view(), name='get-order-detail'),
    path('cancelOrder', views.CancelOrderView.as_view(), name='cancel-order'),
    path('refund', views.RefundOrderView.as_view(), name='refund-order'),
    path('againPay', views.AgainPayView.as_view(), name='again-pay'),
    path('getPayStatus', views.get_pay_status, name='get-pay-status'),
    path('callback', views.payment_callback, name='payment-callback'),
    path('getLive', views.get_nearest_store, name='get-nearest-store'),
    
    # New member benefits endpoints
    path('previewBenefits', views.preview_member_benefits, name='preview-member-benefits'),
]