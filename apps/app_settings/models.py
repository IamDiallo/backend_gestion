from django.db import models
from django.contrib.auth.models import User


class ProductCategory(models.Model):
    """Product categories for inventory organization"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='settings_product_categories')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Catégorie de produit"
        verbose_name_plural = "Catégories de produits"
        db_table = 'gestion_api_productcategory'  # Use existing table


class ExpenseCategory(models.Model):
    """Expense categories for financial tracking"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='settings_expense_categories')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Expense categories"
        db_table = 'gestion_api_expensecategory'  # Use existing table


class UnitOfMeasure(models.Model):
    """Units of measure for products (kg, liters, pieces, etc.)"""
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='settings_units')
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
    class Meta:
        verbose_name = "Unité de mesure"
        verbose_name_plural = "Unités de mesure"
        db_table = 'gestion_api_unitofmeasure'  # Use existing table


class Currency(models.Model):
    """Currencies for multi-currency support"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)
    symbol = models.CharField(max_length=5)
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "Devise"
        verbose_name_plural = "Currencies"
        db_table = 'gestion_api_currency'  # Use existing table


class PaymentMethod(models.Model):
    """Payment methods (cash, bank transfer, check, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mode de paiement"
        verbose_name_plural = "Modes de paiement"
        db_table = 'gestion_api_paymentmethod'  # Use existing table


class PriceGroup(models.Model):
    """Price groups for client discounts"""
    name = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Groupe de prix"
        verbose_name_plural = "Groupes de prix"
        db_table = 'gestion_api_pricegroup'  # Use existing table


class ChargeType(models.Model):
    """Types of charges that can be added to sales (delivery, service, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Type de charge"
        verbose_name_plural = "Types de charge"
        db_table = 'gestion_api_chargetype'  # Use existing table
