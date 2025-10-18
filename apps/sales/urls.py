from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    SaleViewSet,
    DeliveryNoteViewSet,
    SaleChargeViewSet,
    InvoiceViewSet,
    QuoteViewSet,
    reports_sales
)

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'delivery-notes', DeliveryNoteViewSet, basename='delivery-note')
router.register(r'sale-charges', SaleChargeViewSet, basename='sale-charge')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'quotes', QuoteViewSet, basename='quote')

urlpatterns = [
    path('reports/', reports_sales, name='sales-reports'),
] + router.urls
