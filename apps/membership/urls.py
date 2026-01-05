from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.MembershipStatusView.as_view(), name='membership-status'),
    path('benefits/', views.MembershipBenefitsView.as_view(), name='membership-benefits'),
    path('upgrade-history/', views.TierUpgradeHistoryView.as_view(), name='upgrade-history'),
]