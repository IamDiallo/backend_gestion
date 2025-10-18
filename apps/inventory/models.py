from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.app_settings.models import ProductCategory, UnitOfMeasure
from apps.core.models import Zone


class Product(models.Model):
    """
    Produits (finis ou matières premières)
    """
    name = models.CharField(max_length=100)
    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='inventory_products'
    )
    unit = models.ForeignKey(
        UnitOfMeasure, 
        on_delete=models.PROTECT, 
        null=True, 
        db_column='unit',
        related_name='inventory_products'
    )
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    is_raw_material = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='inventory_products_created'
    )

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
        db_table = 'gestion_api_product'
        verbose_name = "Produit"
        verbose_name_plural = "Produits"


class Stock(models.Model):
    """
    Stock par produit et zone
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='stocks'
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.CASCADE, 
        related_name='inventory_stocks'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='inventory_stocks_created'
    )
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.zone.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        db_table = 'gestion_api_stock'
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = ('product', 'zone')


class Supply(models.Model):
    """
    Approvisionnement (ancien modèle)
    """
    reference = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        'partners.Supplier', 
        on_delete=models.CASCADE, 
        related_name='supplies'
    )
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='inventory_supplies')
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Approvisionnement {self.reference} - {self.supplier.name}"
    
    class Meta:
        db_table = 'gestion_api_supply'
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"


class SupplyItem(models.Model):
    """
    Élément d'approvisionnement (ancien modèle)
    """
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='supply_items')
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
        db_table = 'gestion_api_supplyitem'
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"


class StockSupply(models.Model):
    """
    Approvisionnement de stock (nouveau modèle avec gestion paiements)
    """
    reference = models.CharField(max_length=20, unique=True, blank=True, null=True)
    supplier = models.ForeignKey(
        'partners.Supplier', 
        on_delete=models.PROTECT,
        related_name='inventory_stock_supplies'
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.PROTECT,
        related_name='stock_supplies'
    )
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
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='inventory_stock_supplies_created'
    )
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
        db_table = 'gestion_api_stocksupply'
        verbose_name = "Approvisionnement"
        verbose_name_plural = "Approvisionnements"


class StockSupplyItem(models.Model):
    """
    Éléments d'un approvisionnement de stock
    """
    supply = models.ForeignKey(
        StockSupply, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        related_name='stock_supply_items'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    received_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)], 
        default=0
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    total_price = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        db_table = 'gestion_api_stocksupplyitem'
        verbose_name = "Élément d'approvisionnement"
        verbose_name_plural = "Éléments d'approvisionnement"


class StockCard(models.Model):
    """
    Fiche de stock pour suivre les mouvements
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        related_name='stock_cards'
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.PROTECT,
        related_name='stock_cards'
    )
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
        db_table = 'gestion_api_stockcard'
        verbose_name = "Fiche de stock"
        verbose_name_plural = "Fiches de stock"
        ordering = ['product', 'zone', '-date']


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
        db_table = 'gestion_api_stocktransfer'
        verbose_name = "Transfert de stock"
        verbose_name_plural = "Transferts de stock"


class StockTransferItem(models.Model):
    """
    Éléments d'un transfert de stock
    """
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transferred_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    
    def __str__(self):
        try:
            unit_symbol = self.product.unit.symbol if self.product.unit else ""
        except (AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        db_table = 'gestion_api_stocktransferitem'
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
        db_table = 'gestion_api_inventory'
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"


class InventoryItem(models.Model):
    """
    Éléments d'un inventaire
    """
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    difference = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        try:
            unit_symbol = self.product.unit.symbol if self.product.unit else ""
        except (AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} (Attendu: {self.expected_quantity} {unit_symbol}, Réel: {self.actual_quantity} {unit_symbol})"
    
    class Meta:
        db_table = 'gestion_api_inventoryitem'
        verbose_name = "Élément d'inventaire"
        verbose_name_plural = "Éléments d'inventaire"


class StockReturn(models.Model):
    """
    Retours de produits vendus
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey('sales.Sale', on_delete=models.PROTECT)
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
        db_table = 'gestion_api_stockreturn'
        verbose_name = "Retour de stock"
        verbose_name_plural = "Retours de stock"


class StockReturnItem(models.Model):
    """
    Éléments d'un retour de stock
    """
    stock_return = models.ForeignKey(StockReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        try:
            unit_symbol = self.product.unit.symbol if self.product.unit else ""
        except (AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        db_table = 'gestion_api_stockreturnitem'
        verbose_name = "Élément de retour"
        verbose_name_plural = "Éléments de retour"


# ProductTransfer is an alias for StockTransfer (same functionality)
# Created for backward compatibility with gestion_api imports
class ProductTransfer(StockTransfer):
    """
    Alias for StockTransfer - used for backward compatibility
    Transfert de produits entre zones
    """
    class Meta:
        proxy = True
        verbose_name = "Transfert de produit"
        verbose_name_plural = "Transferts de produits"


class ProductTransferItem(StockTransferItem):
    """
    Alias for StockTransferItem - used for backward compatibility
    Éléments d'un transfert de produit
    """
    class Meta:
        proxy = True
        verbose_name = "Élément de transfert de produit"
        verbose_name_plural = "Éléments de transfert de produit"
