from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment methods
    path('methods/', views.get_payment_methods, name='payment_methods'),
    
    # Payment transactions
    path('create/', views.create_payment, name='create_payment'),
    path('status/<str:transaction_id>/', views.get_payment_status, name='payment_status'),
    path('cancel/<str:transaction_id>/', views.cancel_payment, name='cancel_payment'),
    path('user/payments/', views.get_user_payments, name='user_payments'),
    
    # Refunds
    path('refund/create/', views.create_refund, name='create_refund'),
    path('user/refunds/', views.get_user_refunds, name='user_refunds'),
    
    # WeChat Pay callbacks
    path('callback/wechat/payment/', views.wechat_pay_callback, name='wechat_pay_callback'),
    path('callback/wechat/refund/', views.wechat_refund_callback, name='wechat_refund_callback'),
]