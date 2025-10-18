from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import (
    ProductCategory, ExpenseCategory, UnitOfMeasure,
    Currency, PaymentMethod, PriceGroup, ChargeType
)
from .serializers import (
    ProductCategorySerializer, ExpenseCategorySerializer, UnitOfMeasureSerializer,
    CurrencySerializer, PaymentMethodSerializer, PriceGroupSerializer, ChargeTypeSerializer
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for product categories"""
    queryset = ProductCategory.objects.all().order_by('name')
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for expense categories"""
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    """API endpoint for units of measure"""
    queryset = UnitOfMeasure.objects.all().order_by('name')
    serializer_class = UnitOfMeasureSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CurrencyViewSet(viewsets.ModelViewSet):
    """API endpoint for currencies"""
    queryset = Currency.objects.all().order_by('name')
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """API endpoint for payment methods"""
    queryset = PaymentMethod.objects.all().order_by('name')
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]


class PriceGroupViewSet(viewsets.ModelViewSet):
    """API endpoint for price groups"""
    queryset = PriceGroup.objects.all().order_by('name')
    serializer_class = PriceGroupSerializer
    permission_classes = [IsAuthenticated]


class ChargeTypeViewSet(viewsets.ModelViewSet):
    """API endpoint for charge types"""
    queryset = ChargeType.objects.all().order_by('name')
    serializer_class = ChargeTypeSerializer
    permission_classes = [IsAuthenticated]
