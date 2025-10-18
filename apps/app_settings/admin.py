from django.contrib import admin
from .models import (
    Currency, PaymentMethod, UnitOfMeasure, 
    ProductCategory, PriceGroup, ExpenseCategory, ChargeType
)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'symbol', 'is_base', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_base', 'is_active')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'created_at')
    search_fields = ('name', 'symbol')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_by', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'created_by')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PriceGroup)
class PriceGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percentage', 'description')
    search_fields = ('name', 'description')
    list_filter = ('discount_percentage',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)


@admin.register(ChargeType)
class ChargeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
