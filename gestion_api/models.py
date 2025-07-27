from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

# I. User Profiles
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
        """Check if user has a specific permission through Django's permission system"""
        # Admin users have all permissions
        if self.role == 'admin':
            return True
            
        # Check app_label and codename from the permission code
        if '.' in permission_code:
            app_label, codename = permission_code.split('.')
            return self.user.has_perm(f"{app_label}.{codename}")
        else:
            return self.user.has_perm(permission_code)
    
    def get_all_permissions(self):
        """Get all permissions for this user, including from group"""
        # Start with direct user permissions
        permissions = set()
        
        # Add all direct permissions assigned to the user
        for perm in self.user.user_permissions.all():
            permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
        
        # Add permissions from Django groups
        for group in self.user.groups.all():
            for perm in group.permissions.all():
                permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
                
        return permissions

# Signal to create or update user profile when user is saved
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile whenever the User model is saved
    """
    print(f"Signal triggered for user {instance.username} - created={created}")
    try:
        if created:
            # For new users, create a profile
            profile = UserProfile.objects.create(user=instance)
            print(f"Created new profile for {instance.username}: {profile.id}")
        else:
            # For existing users, get or create the profile
            profile, profile_created = UserProfile.objects.get_or_create(user=instance)
            if profile_created:
                print(f"Created missing profile for existing user {instance.username}: {profile.id}")
            else:
                print(f"Found existing profile for {instance.username}: {profile.id}")
    except Exception as e:
        print(f"Error in create_or_update_user_profile signal: {e}")

# II. Parameters
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
    
    class Meta:
        verbose_name = "Unité de mesure"
        verbose_name_plural = "Unités de mesure"

class Zone(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True, null=True)  # Ensure this field exists
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Zone/Magasin"
        verbose_name_plural = "Zones/Magasins"

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

class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_from', null=True)
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_to', null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
    date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.from_currency.code} to {self.to_currency.code}: {self.rate}"
    
    class Meta:
        verbose_name = "Taux de change"
        verbose_name_plural = "Taux de change"

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mode de paiement"
        verbose_name_plural = "Modes de paiement"

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

class PriceGroup(models.Model):
    name = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Groupe de prix"
        verbose_name_plural = "Groupes de prix"

# III. Products
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
        # Get the first two characters of the category name as prefix
        if self.category and self.category.name:
            # Get first two characters, ensuring we have at least two by padding with 'X' if needed
            category_name = self.category.name.strip()
            if not category_name:
                prefix = "PR"  # Default if category name is empty
            else:
                prefix = category_name[:2].upper().ljust(2, 'X')
        else:
            prefix = "PR"  # Default if no category
            
        # Get the last ID and increment by 1
        last_product = Product.objects.order_by('-id').first()
        next_id = 1 if not last_product else last_product.id + 1
        
        # Format: AA-0001 (where AA are the first two letters of category name)
        return f"{prefix}-{next_id:04d}"
    
    def generate_qr_code_data(self):
        """
        Generate the data to be encoded in the QR code
        """
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


# IV. Third Parties
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

class Employee(models.Model):
    """
    Modèle pour les employés
    """
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

# V. Stock
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
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

class SupplyItem(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)  # Fixed missing parenthesis
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"

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

class Inventory(models.Model):
    """
    Inventaire de stock
    """
    reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé')
    ])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Inventaire {self.reference} - {self.zone.name}"
    
    class Meta:
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"

class InventoryItem(models.Model):
    """
    Éléments d'un inventaire
    """
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    difference = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} (Attendu: {self.expected_quantity} {unit_symbol}, Réel: {self.actual_quantity} {unit_symbol})"
    
    class Meta:
        verbose_name = "Élément d'inventaire"
        verbose_name_plural = "Éléments d'inventaire"

class StockReturn(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey('Sale', on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"Return {self.reference} - {self.sale.reference}"
    
    class Meta:
        verbose_name = "Retour de stock"
        verbose_name_plural = "Retours de stock"

class StockReturnItem(models.Model):
    stock_return = models.ForeignKey(StockReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément de retour"
        verbose_name_plural = "Éléments de retour"

# VI. Sales
class Sale(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('payment_pending', 'Paiement en attente'),
        ('partially_paid', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Non payé'),
        ('partially_paid', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('overpaid', 'Surpayé')
    ]
    
    WORKFLOW_STATE_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('payment_pending', 'Paiement en attente'),
        ('partially_paid', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),        
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé')
    ]
    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    workflow_state = models.CharField(max_length=50, choices=WORKFLOW_STATE_CHOICES, default='draft')
    delivery_notes = models.ManyToManyField('DeliveryNote', related_name='sales', blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) 
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Sale {self.reference} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        # Only generate a reference if this is a new object (no ID yet) and reference is empty
        if not self.pk and not self.reference:
            from django.db import transaction
            
            # Use a transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                # Get the current year
                year = timezone.now().year
                # Lock the table to prevent concurrent reference generation
                last_sale = Sale.objects.filter(reference__startswith=f"VNT-{year}-").select_for_update().order_by('-reference').first()
                
                if last_sale:
                    try:
                        # Extract the number part and increment
                        last_number = int(last_sale.reference.split('-')[-1])
                        next_number = last_number + 1
                    except (ValueError, IndexError):
                        # If parsing fails, count all sales for this year and add 1
                        count = Sale.objects.filter(reference__startswith=f"VNT-{year}-").count()
                        next_number = count + 1
                else:
                    # First sale of the year
                    next_number = 1
                
                # Format the reference (ensure it's at least 3 digits)
                self.reference = f"VNT-{year}-{next_number:03d}"
                
                # Double check that this reference isn't already used 
                # (extra safety check)
                while Sale.objects.filter(reference=self.reference).exists():
                    next_number += 1
                    self.reference = f"VNT-{year}-{next_number:03d}"
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Élément de vente"
        verbose_name_plural = "Éléments de vente"

# VII. Production
class Production(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='productions')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Production {self.reference} - {self.product.name}"
    
    class Meta:
        verbose_name = "Production"
        verbose_name_plural = "Productions"

class ProductionMaterial(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE, related_name='materials')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except UnitOfMeasure.DoesNotExist:
            unit_symbol = ""
        except Exception:
            unit_symbol = "units"
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        verbose_name = "Matière première utilisée"
        verbose_name_plural = "Matières premières utilisées"

# VIII. Treasury
class Expense(models.Model):
    """
    Modèle pour les dépenses
    """
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

class ClientPayment(models.Model):
    """
    Règlement client
    """
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

class SupplierPayment(models.Model):
    """
    Règlement fournisseur
    """
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

class AccountTransfer(models.Model):
    """
    Virement entre comptes
    """
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

class CashReceipt(models.Model):
    """
    Encaissement
    """
    reference = models.CharField(max_length=20, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, null=True, blank=True, related_name='receipts')
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

class CashPayment(models.Model):
    """
    Décaissement
    """
    reference = models.CharField(max_length=20, unique=True)  # Fixed: maxlength -> max_lengthlength
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(default="")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Décaissement {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Décaissement"
        verbose_name_plural = "Décaissements"

class AccountStatement(models.Model):
    """
    Relevé de compte pour suivre les mouvements
    """
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

# VII. Vente - Modèles supplémentaires
class DeliveryNote(models.Model):
    """
    Bon de livraison pour les commandes
    """
    reference = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé')
    ])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Livraison {self.reference} - {self.client.name}"
    
    class Meta:
        verbose_name = "Bon de livraison"
        verbose_name_plural = "Bons de livraison"

class DeliveryNoteItem(models.Model):
    """
    Éléments d'un bon de livraison
    """
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        verbose_name = "Élément de livraison"
        verbose_name_plural = "Éléments de livraison"

class ChargeType(models.Model):
    """
    Type de charge pour les ventes
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Type de charge"
        verbose_name_plural = "Types de charge"

class SaleCharge(models.Model):
    """
    Charges additionnelles sur une vente
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='charges')
    charge_type = models.ForeignKey(ChargeType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.charge_type.name} - {self.amount}"
    
    class Meta:
        verbose_name = "Charge de vente"
        verbose_name_plural = "Charges de vente"

# V. Tiers - Modèles supplémentaires
class ClientGroup(models.Model):
    """
    Groupe de clients
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Groupe de clients"
        verbose_name_plural = "Groupes de clients"

# VI. Stocks
class StockSupply(models.Model):
    """
    Modèle pour les approvisionnements de stock
    """
    # Allow blank and null temporarily for backend generation
    reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('partial', 'Partiellement reçu'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé')
    ])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Approvisionnement {self.reference} - {self.supplier.name}"
    
    class Meta:
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"

class StockSupplyItem(models.Model):
    """
    Éléments d'un approvisionnement
    """
    supply = models.ForeignKey(StockSupply, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    
    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"

class StockTransfer(models.Model):
    """
    Transfert de produits entre zones
    """
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
    """
    Éléments d'un transfert de stock
    """
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
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

class StockCard(models.Model):
    """
    Fiche de stock pour suivre les mouvements de stock
    """
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
    reference = models.CharField(max_length=50)  # Référence du document source
    quantity_in = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Fiche {self.product.name} - {self.date} - {self.get_transaction_type_display()}"
    
    class Meta:
        verbose_name = "Fiche de stock"
        verbose_name_plural = "Fiches de stock"
        ordering = ['product', 'zone', '-date']

class Invoice(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='invoices')
    date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=[
            ('draft', 'Brouillon'),
            ('sent', 'Envoyé'),
            ('paid', 'Payé'),
            ('overdue', 'En retard'),
            ('cancelled', 'Annulé')
        ],
        default='draft'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference


class Quote(models.Model):
    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='quotes')
    date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=[
            ('draft', 'Brouillon'),
            ('sent', 'Envoyé'),
            ('accepted', 'Accepté'),
            ('rejected', 'Rejeté'),
            ('expired', 'Expiré')
        ],
        default='draft'
    )
    is_converted = models.BooleanField(default=False, help_text="Si ce devis a été converti en vente")
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Only generate a reference if this is a new object (no ID yet) and reference is empty
        if not self.pk and not self.reference:
            from django.db import transaction
            
            # Use a transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                # Get the current year
                year = timezone.now().year
                # Lock the table to prevent concurrent reference generation
                last_quote = Quote.objects.filter(reference__startswith=f"DEV-{year}-").select_for_update().order_by('-reference').first()
                
                if last_quote:
                    try:
                        # Extract the number part and increment
                        last_number = int(last_quote.reference.split('-')[-1])
                        next_number = last_number + 1
                    except (ValueError, IndexError):
                        # If parsing fails, count all quotes for this year and add 1
                        count = Quote.objects.filter(reference__startswith=f"DEV-{year}-").count()
                        next_number = count + 1
                else:
                    # First quote of the year
                    next_number = 1
                
                # Format the reference (ensure it's at least 3 digits)
                self.reference = f"DEV-{year}-{next_number:03d}"
                
                # Double check that this reference isn't already used 
                # (extra safety check)
                while Quote.objects.filter(reference=self.reference).exists():
                    next_number += 1
                    self.reference = f"DEV-{year}-{next_number:03d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Fix: Get the UnitOfMeasure object using the unit ID from product
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.quote.reference} - {self.product.name} ({self.quantity} {unit_symbol})"

# VIII. Financial Reporting
class CashFlow(models.Model):
    """
    Model to track all cash movements in the system
    """
    FLOW_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('client_payment', 'Client Payment'),
        ('supplier_payment', 'Supplier Payment'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    flow_type = models.CharField(max_length=20, choices=FLOW_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='cash_flows')
    related_document_type = models.CharField(max_length=50, blank=True, null=True)
    related_document_id = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_flow_type_display()} - {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Cash Flow"
        verbose_name_plural = "Cash Flows"

class BankReconciliation(models.Model):
    """
    Model for bank reconciliation
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    bank_statement_balance = models.DecimalField(max_digits=15, decimal_places=2)
    book_balance = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reconciliation {self.reference} - {self.account.name}"
    
    class Meta:
        verbose_name = "Bank Reconciliation"
        verbose_name_plural = "Bank Reconciliations"

class BankReconciliationItem(models.Model):
    """
    Model for bank reconciliation items
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('check', 'Check'),
        ('fee', 'Fee'),
        ('interest', 'Interest'),
        ('transfer', 'Transfer'),
        ('other', 'Other'),
    ]
    
    reconciliation = models.ForeignKey(BankReconciliation, on_delete=models.CASCADE, related_name='items')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    transaction_date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    is_reconciled = models.BooleanField(default=False)
    reference_document = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.transaction_date} - {self.amount}"
    
    class Meta:
        verbose_name = "Reconciliation Item"
        verbose_name_plural = "Reconciliation Items"

class FinancialReport(models.Model):
    """
    Model for storing financial report configurations
    """
    REPORT_TYPES = [
        ('income_statement', 'Income Statement'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow Statement'),
        ('receivables', 'Accounts Receivable'),
        ('payables', 'Accounts Payable'),
        ('custom', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    parameters = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
    
    class Meta:
        verbose_name = "Financial Report"
        verbose_name_plural = "Financial Reports"

class AccountPayment(models.Model):
    """
    Payment using client account balance
    """
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField()
    reference = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Account Payment {self.reference} - {self.amount}"
    
    class Meta:
        verbose_name = "Account Payment"
        verbose_name_plural = "Account Payments"