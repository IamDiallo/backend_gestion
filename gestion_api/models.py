from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

# I. User Profiles
# MIGRATED TO apps.core
"""
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('consultant', 'Consultant'),
        ('supervisor', 'Supervisor'),
        ('commercial', 'Commercial'),
        ('cashier', 'Cashier'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, related_name='users')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def has_permission(self, permission_code):
        if self.role == 'admin':
            return True
            
        if '.' in permission_code:
            app_label, codename = permission_code.split('.')
            return self.user.has_perm(f"{app_label}.{codename}")
        else:
            return self.user.has_perm(permission_code)
    
    def get_all_permissions(self):
        permissions = set()
        
        for perm in self.user.user_permissions.all():
            permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
        
        for group in self.user.groups.all():
            for perm in group.permissions.all():
                permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
                
        return permissions
"""
from apps.core.models import UserProfile

# Signal moved to apps.core.signals - using core app's signal handler
# This avoids duplicate profile creation

# II. Parameters
# MIGRATED TO apps.app_settings - Models commented out to avoid conflicts
# Uncomment if you need to rollback the migration

"""
class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Catégorie de produit"
        verbose_name_plural = "Catégories de produits"

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Expense categories"

class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)  # Fix: changed maxlength to max_length
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
"""

# Import from new app_settings location
from apps.app_settings.models import ProductCategory, ExpenseCategory, UnitOfMeasure

# MIGRATED TO apps.core
"""
class Zone(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Zone/Magasin"
        verbose_name_plural = "Zones/Magasins"
"""
from apps.core.models import Zone

# MIGRATED TO apps.app_settings - Models commented out to avoid conflicts
"""
class Currency(models.Model):
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


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mode de paiement"
        verbose_name_plural = "Modes de paiement"
"""

# Import from new app_settings location
from apps.app_settings.models import Currency, PaymentMethod

# MIGRATED TO apps.treasury
"""
class Account(models.Model):
    ACCOUNT_TYPES = [
        ('internal', 'Compte Interne'),
        ('bank', 'Compte Bancaire'),
        ('cash', 'Caisse'),
        ('client', 'Compte Client'),
        ('supplier', 'Compte Fournisseur'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"
    
    class Meta:
        verbose_name = "Compte"
        verbose_name_plural = "Comptes"
"""
from apps.treasury.models import Account

# MIGRATED TO apps.app_settings
"""
class PriceGroup(models.Model):
    name = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Groupe de prix"
        verbose_name_plural = "Groupes de prix"
"""

# Import from new app_settings location
from apps.app_settings.models import PriceGroup

# III. Products
# MIGRATED TO apps.inventory
"""
class Product(models.Model):
    name = models.CharField(max_length=100)
    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, db_column='unit')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    is_raw_material = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.reference:
            last_product = Product.objects.order_by('id').last()
            if last_product:
                self.reference = f"PROD-{last_product.id + 1:04d}"
            else:
                self.reference = "PROD-0001"
        super().save(*args, **kwargs)

    def generate_reference(self):
        if self.category and self.category.name:
            category_name = self.category.name.strip()
            if not category_name:
                prefix = "PR"
            else:
                prefix = category_name[:2].upper().ljust(2, 'X')
        else:
            prefix = "PR"
            
        last_product = Product.objects.order_by('-id').first()
        next_id = 1 if not last_product else last_product.id + 1
        
        return f"{prefix}-{next_id:04d}"
    
    def generate_qr_code_data(self):
        return {
            'id': self.id,
            'name': self.name,
            'reference': self.reference,
            'category': self.category.name if self.category else '',
            'unit': self.unit.symbol if self.unit else '',
            'price': str(self.selling_price)
        }

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
"""
from apps.inventory.models import Product


# IV. Third Parties
# MIGRATED TO apps.partners
"""
class Client(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    price_group = models.ForeignKey(PriceGroup, on_delete=models.SET_NULL, null=True)
    account = models.OneToOneField(Account, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
"""
from apps.partners.models import Client

# MIGRATED TO apps.partners
"""
class Supplier(models.Model):
    name = models.CharField(max_length=200)  # Fix: changed maxlength to max_length
    contact_person = models.CharField(max_length=100, blank=True)  # Fix: changed maxlength to max_length
    phone = models.CharField(max_length=20)  # Fix: changed maxlength to max_length
    email = models.EmailField(blank=True)
    address = models.TextField()
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='supplier')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
"""
from apps.partners.models import Supplier

# MIGRATED TO apps.partners
"""
class Employee(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, default="Général")
    email = models.EmailField(default="")
    phone = models.CharField(max_length=20)
    address = models.TextField()
    hire_date = models.DateField(default=timezone.now)
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.position}"
    
    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
"""
from apps.partners.models import Employee

# V. Stock
# MIGRATED TO apps.inventory
"""
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.zone.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = ('product', 'zone')
"""
from apps.inventory.models import Stock

# MIGRATED TO apps.inventory
"""
class Supply(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplies')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Approvisionnement {self.reference} - {self.supplier.name}"
    
    class Meta:
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"
"""
from apps.inventory.models import Supply

# MIGRATED TO apps.inventory
"""
class SupplyItem(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"
"""
from apps.inventory.models import SupplyItem

# IV. Inventory
# MIGRATED TO apps.inventory - Models commented out to avoid conflicts
"""
class ProductTransfer(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    source_zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='transfers_out')
    destination_zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='transfers_in')
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Transfert {self.reference} - {self.source_zone.name} → {self.destination_zone.name}"
    
    class Meta:
        verbose_name = "Transfert de produit"
        verbose_name_plural = "Transferts de produits"

class ProductTransferItem(models.Model):
    transfer = models.ForeignKey(ProductTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément de transfert"
        verbose_name_plural = "Éléments de transfert"
"""
from apps.inventory.models import (
    StockTransfer, StockTransferItem, Inventory, InventoryItem, 
    StockReturn, StockReturnItem, ProductTransfer, ProductTransferItem
)

# VI. Sales
# MIGRATED TO apps.sales
"""
class Sale(models.Model):
    STATUS_CHOICES = [...]
    [Full model definition omitted - 96 lines]
    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
"""
from apps.sales.models import Sale

# MIGRATED TO apps.sales
"""
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément de vente"
        verbose_name_plural = "Éléments de vente"
"""
from apps.sales.models import SaleItem

# VII. Production
# VII. Production
# MIGRATED TO apps.production
"""
class Production(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='productions')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Production"
        verbose_name_plural = "Productions"
"""
from apps.production.models import Production

# MIGRATED TO apps.production
"""
class ProductionMaterial(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE, related_name='materials')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = "Matière première utilisée"
        verbose_name_plural = "Matières premières utilisées"
"""
from apps.production.models import ProductionMaterial

# VIII. Treasury
# MIGRATED TO apps.treasury
"""
class Expense(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField()
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé')
    ])
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Fixed missing parenthesis
    
    def __str__(self):
        return f"Dépense {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
"""
from apps.treasury.models import Expense

# MIGRATED TO apps.treasury
"""
class ClientPayment(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Règlement {self.reference} - {self.client.name} - {self.amount}"
    
    class Meta:
        verbose_name = "Règlement client"
        verbose_name_plural = "Règlements clients"
"""
from apps.treasury.models import ClientPayment

# MIGRATED TO apps.treasury
"""
class SupplierPayment(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Règlement {self.reference} - {self.supplier.name} - {self.amount}"
    
    class Meta:
        verbose_name = "Règlement fournisseur"
        verbose_name_plural = "Règlements fournisseurs"
"""
from apps.treasury.models import SupplierPayment

# MIGRATED TO apps.treasury
"""
class AccountTransfer(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfers_from', null=True)
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfers_to', null=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, validators=[MinValueValidator(0)], default=1)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Virement {self.reference} - {self.from_account.name} → {self.to_account.name} - {self.amount}"
    
    class Meta:
        verbose_name = "Virement"
        verbose_name_plural = "Virements"
"""
from apps.treasury.models import AccountTransfer

# MIGRATED TO apps.treasury
"""
class CashReceipt(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True, blank=True, related_name='receipts')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    description = models.TextField(default="")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Encaissement {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Encaissement"
        verbose_name_plural = "Encaissements"
"""
from apps.treasury.models import CashReceipt


# MIGRATED TO apps.treasury
"""
class SupplierCashPayment(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True)  # Company account paying
    supply = models.ForeignKey('StockSupply', on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    description = models.TextField(default="")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Paiement fournisseur {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Paiement fournisseur"
        verbose_name_plural = "Paiements fournisseurs"
"""
from apps.treasury.models import SupplierCashPayment


# MIGRATED TO apps.treasury
"""
class AccountStatement(models.Model):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=[
        ('client_payment', 'Règlement client'),
        ('supplier_payment', 'Règlement fournisseur'),
        ('transfer_in', 'Virement entrant'),
        ('transfer_out', 'Virement sortant'),
        ('cash_receipt', 'Encaissement'),
        ('cash_payment', 'Décaissement'),
        ('expense', 'Dépense'),
        ('sale', 'Vente'),
        ('purchase', 'Achat'),
        ('deposit', 'Dépôt')
    ])
    reference = models.CharField(max_length=50)  # Référence du document source
    description = models.TextField(blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f"Mouvement {self.account.name} - {self.date} - {self.get_transaction_type_display()}"
    
    class Meta:
        verbose_name = "Mouvement de compte"
        verbose_name_plural = "Mouvements de compte"
        ordering = ['account', '-date']
"""
from apps.treasury.models import AccountStatement

# VII. Vente - Modèles supplémentaires
# MIGRATED TO apps.sales
"""
class DeliveryNote(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[...])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Bon de livraison"
        verbose_name_plural = "Bons de livraison"
"""
from apps.sales.models import DeliveryNote

# MIGRATED TO apps.sales
"""
class DeliveryNoteItem(models.Model):
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = "Élément de livraison"
        verbose_name_plural = "Éléments de livraison"
"""
from apps.sales.models import DeliveryNoteItem

# MIGRATED TO apps.app_settings
"""
class ChargeType(models.Model):
    \"\"\"
    Type de charge pour les ventes
    \"\"\"
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Type de charge"
        verbose_name_plural = "Types de charge"
"""

# Import from new app_settings location
from apps.app_settings.models import ChargeType

# MIGRATED TO apps.sales
"""
class SaleCharge(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='charges')
    charge_type = models.ForeignKey(ChargeType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Charge de vente"
        verbose_name_plural = "Charges de vente"
"""
from apps.sales.models import SaleCharge

# V. Tiers - Modèles supplémentaires
# MIGRATED TO apps.partners
"""
class ClientGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Groupe de clients"
        verbose_name_plural = "Groupes de clients"
"""
from apps.partners.models import ClientGroup

# VI. Stocks
# MIGRATED TO apps.inventory
"""
class StockSupply(models.Model):
    reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('partial', 'Partiellement reçu'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé')
    ])
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Non payé'),
            ('partially_paid', 'Partiellement payé'),
            ('paid', 'Payé'),
            ('overpaid', 'Surpayé')
        ],
        default='unpaid'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Approvisionnement {self.reference} - {self.supplier.name}"
    
    def get_total_amount(self):
        from django.db.models import Sum
        return self.items.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
    
    def update_payment_status(self):
        if self.paid_amount >= self.total_amount and self.total_amount > 0:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partially_paid'
        else:
            self.payment_status = 'unpaid'
        self.remaining_amount = self.total_amount - self.paid_amount
    
    class Meta:
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"
"""
from apps.inventory.models import StockSupply

# MIGRATED TO apps.inventory
"""
class StockSupplyItem(models.Model):
    supply = models.ForeignKey(StockSupply, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"
"""
from apps.inventory.models import StockSupplyItem

# MIGRATED TO apps.inventory - Models commented out to avoid conflicts
"""
class StockTransfer(models.Model):
    \"\"\"
    Transfert de produits entre zones
    \"\"\"
    reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    from_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='transfers_from')
    to_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='transfers_to')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('partial', 'Partiellement transféré'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé')
    ])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Transfert {self.reference} - {self.from_zone.name} → {self.to_zone.name}"
    
    class Meta:
        verbose_name = "Transfert de stock"
        verbose_name_plural = "Transferts de stock"

class StockTransferItem(models.Model):
    \"\"\"
    Éléments d'un transfert de stock
    \"\"\"
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transferred_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        verbose_name = "Élément de transfert"
        verbose_name_plural = "Éléments de transfert"
"""
from apps.inventory.models import StockTransfer, StockTransferItem

# MIGRATED TO apps.inventory
"""
class StockCard(models.Model):
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=[
        ('supply', 'Approvisionnement'),
        ('sale', 'Vente'),
        ('transfer_in', 'Transfert entrant'),
        ('transfer_out', 'Transfert sortant'),
        ('inventory', 'Ajustement d\'inventaire'),
        ('production', 'Production'),
        ('return', 'Retour')
    ])
    reference = models.CharField(max_length=50)
    quantity_in = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Fiche {self.product.name} - {self.date} - {self.get_transaction_type_display()}"
    
    class Meta:
        verbose_name = "Fiche de stock"
        verbose_name_plural = "Fiches de stock"
        ordering = ['product', 'zone', '-date']
"""
from apps.inventory.models import StockCard

# MIGRATED TO apps.sales
"""
class Invoice(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='invoices')
    date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=[...])
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
"""
from apps.sales.models import Invoice

# MIGRATED TO apps.sales
"""
class Quote(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='quotes')
    date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=[...])
    is_converted = models.BooleanField(default=False)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    [save method with auto-generated DEV-YYYY-NNN reference]
"""
from apps.sales.models import Quote

# MIGRATED TO apps.sales
"""
class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
"""
from apps.sales.models import QuoteItem
