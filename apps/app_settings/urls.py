from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'product-categories', views.ProductCategoryViewSet, basename='productcategory')
router.register(r'expense-categories', views.ExpenseCategoryViewSet, basename='expensecategory')
router.register(r'units-of-measure', views.UnitOfMeasureViewSet, basename='unitofmeasure')
router.register(r'currencies', views.CurrencyViewSet, basename='currency')
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='paymentmethod')
router.register(r'price-groups', views.PriceGroupViewSet, basename='pricegroup')
router.register(r'charge-types', views.ChargeTypeViewSet, basename='chargetype')

urlpatterns = [
    path('', include(router.urls)),
]
