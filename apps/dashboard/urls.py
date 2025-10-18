"""
Dashboard App URLs
Aggregated endpoints for dashboard display
"""

from django.urls import path
from . import views

urlpatterns = [
    # Core dashboard endpoints
    path('stats/', views.dashboard_stats, name='dashboard-stats'),
    path('inventory/', views.inventory_stats, name='dashboard-inventory'),
    path('low-stock/', views.low_stock_products, name='dashboard-low-stock'),
    path('recent-sales/', views.recent_sales, name='dashboard-recent-sales'),
    
    # Additional dashboard endpoints
    path('top-products/', views.top_products, name='dashboard-top-products'),
    path('revenue-trend/', views.revenue_trend, name='dashboard-revenue-trend'),
    path('client-activity/', views.client_activity, name='dashboard-client-activity'),
    path('pending-payments/', views.pending_payments, name='dashboard-pending-payments'),
]
