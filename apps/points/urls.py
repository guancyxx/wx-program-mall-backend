from django.urls import path
from . import views

app_name = 'points'

urlpatterns = [
    # User-facing endpoints
    path('balance/', views.get_points_balance, name='balance'),
    path('summary/', views.get_points_summary, name='summary'),
    path('transactions/', views.get_points_transactions, name='transactions'),
    path('redeem/validate/', views.validate_points_redemption, name='validate_redemption'),
    path('redeem/', views.redeem_points, name='redeem'),
    path('max-redeemable/', views.get_max_redeemable_points, name='max_redeemable'),
    path('rules/', views.get_points_rules, name='rules'),
    path('award-review/', views.award_review_points, name='award_review'),
    
    # Internal endpoints (for integration with other apps)
    path('internal/award-purchase/', views.internal_award_purchase_points, name='internal_award_purchase'),
    path('internal/award-registration/', views.internal_award_registration_points, name='internal_award_registration'),
]