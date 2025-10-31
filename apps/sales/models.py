from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.app_settings.models import ChargeType, UnitOfMeasure
from apps.partners.models import Client
from apps.inventory.models import Product
from apps.core.models import Zone
from apps.treasury.models import Account


class Sale(models.Model):
    """
    Ventes
    """
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
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT,
        related_name='sales'
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.PROTECT,
        related_name='sales'
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    workflow_state = models.CharField(max_length=50, choices=WORKFLOW_STATE_CHOICES, default='draft')
    delivery_notes = models.ManyToManyField('DeliveryNote', related_name='sales_m2m', blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) 
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='sales_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Sale {self.reference} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        # Check if this is a cancellation (status change to 'cancelled')
        if self.pk:  # Only for existing sales
            old_sale = Sale.objects.get(pk=self.pk)
            if old_sale.status != 'cancelled' and self.status == 'cancelled':
                # Sale is being cancelled - restore stock and reverse payments
                self._handle_cancellation()
        
        if self.status == 'confirmed':
            self.status = 'payment_pending'
        if not self.pk and not self.reference:
            from django.db import transaction
            with transaction.atomic():
                year = timezone.now().year
                last_sale = Sale.objects.filter(reference__startswith=f"VNT-{year}-").select_for_update().order_by('-reference').first()
                if last_sale:
                    try:
                        last_number = int(last_sale.reference.split('-')[-1])
                        next_number = last_number + 1
                    except (ValueError, IndexError):
                        count = Sale.objects.filter(reference__startswith=f"VNT-{year}-").count()
                        next_number = count + 1
                else:
                    next_number = 1
                self.reference = f"VNT-{year}-{next_number:03d}"
                while Sale.objects.filter(reference=self.reference).exists():
                    next_number += 1
                    self.reference = f"VNT-{year}-{next_number:03d}"
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Handle safe deletion - restore stock and reverse payments"""
        from apps.inventory.models import Stock, StockCard
        from apps.treasury.models import AccountStatement, CashReceipt
        
        # Restore stock for each sale item and create StockCard entries
        for item in self.items.all():
            stock, created = Stock.objects.get_or_create(
                product=item.product,
                zone=self.zone,
                defaults={'quantity': 0}
            )
            stock.quantity += item.quantity
            stock.save()
            
            # Create StockCard entry for the return
            StockCard.objects.create(
                product=item.product,
                zone=self.zone,
                date=timezone.now().date(),
                transaction_type='return',
                reference=f"RETURN-{self.reference}",
                quantity_in=item.quantity,
                quantity_out=0,
                notes=f"Sale deletion return: {self.reference}"
            )
        
        # Reverse payments - create reversing AccountStatement entries
        self._reverse_payments()
        
        # Delete the sale itself
        super().delete(*args, **kwargs)
    
    def _reverse_payments(self):
        """Reverse all payment transactions for this sale"""
        from apps.treasury.models import AccountStatement, CashReceipt
        
        # Get all cash receipts for this sale
        cash_receipts = CashReceipt.objects.filter(sale=self)
        
        for receipt in cash_receipts:
            # Get the client account
            try:
                client_account = Account.objects.get(account_type='client', client=self.client)
            except Account.DoesNotExist:
                continue
            
            # Get the company account
            company_account = receipt.account
            
            # Get last statements for both accounts
            last_client_statement = AccountStatement.objects.filter(
                account=client_account
            ).order_by('-date', '-id').first()
            client_balance = last_client_statement.balance if last_client_statement else Decimal('0.00')
            
            last_company_statement = AccountStatement.objects.filter(
                account=company_account
            ).order_by('-date', '-id').first()
            company_balance = last_company_statement.balance if last_company_statement else Decimal('0.00')
            
            # Create reversing entries
            # Credit client account (reverse the debit)
            new_client_balance = client_balance + receipt.allocated_amount
            AccountStatement.objects.create(
                account=client_account,
                date=timezone.now().date(),
                transaction_type='sale',
                reference=f"REV-{receipt.reference}",
                description=f"Annulation paiement vente {self.reference}",
                credit=receipt.allocated_amount,
                debit=0,
                balance=new_client_balance,
            )
            client_account.current_balance = new_client_balance
            client_account.save(update_fields=['current_balance'])
            
            # Debit company account (reverse the credit)
            new_company_balance = company_balance - receipt.allocated_amount
            AccountStatement.objects.create(
                account=company_account,
                date=timezone.now().date(),
                transaction_type='sale',
                reference=f"REV-{receipt.reference}",
                description=f"Annulation encaissement vente {self.reference}",
                credit=0,
                debit=receipt.allocated_amount,
                balance=new_company_balance,
            )
            company_account.current_balance = new_company_balance
            company_account.save(update_fields=['current_balance'])
    
    def _handle_cancellation(self):
        """Handle sale cancellation - restore stock and reverse payments"""
        from apps.inventory.models import Stock, StockCard
        
        # Restore stock for each sale item and create StockCard entries
        for item in self.items.all():
            stock, created = Stock.objects.get_or_create(
                product=item.product,
                zone=self.zone,
                defaults={'quantity': 0}
            )
            stock.quantity += item.quantity
            stock.save()
            
            # Create StockCard entry for the cancellation return
            StockCard.objects.create(
                product=item.product,
                zone=self.zone,
                date=timezone.now().date(),
                transaction_type='return',
                reference=f"CANCEL-{self.reference}",
                quantity_in=item.quantity,
                quantity_out=0,
                notes=f"Sale cancellation: {self.reference}"
            )
        
        # Reverse payments
        self._reverse_payments()

    class Meta:
        db_table = 'gestion_api_sale'
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"


class SaleItem(models.Model):
    """
    Éléments d'une vente
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='sale_items'
    )
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
        db_table = 'gestion_api_saleitem'
        verbose_name = "Élément de vente"
        verbose_name_plural = "Éléments de vente"


class DeliveryNote(models.Model):
    """
    Bon de livraison
    """
    reference = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT,
        related_name='sales_delivery_notes'
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.PROTECT,
        related_name='delivery_notes'
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé')
    ])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales_delivery_notes_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Livraison {self.reference} - {self.client.name}"
    
    class Meta:
        db_table = 'gestion_api_deliverynote'
        verbose_name = "Bon de livraison"
        verbose_name_plural = "Bons de livraison"


class DeliveryNoteItem(models.Model):
    """
    Éléments d'un bon de livraison
    """
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        related_name='delivery_note_items'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        db_table = 'gestion_api_deliverynoteitem'
        verbose_name = "Élément de livraison"
        verbose_name_plural = "Éléments de livraison"


class SaleCharge(models.Model):
    """
    Charges additionnelles sur une vente
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='charges')
    charge_type = models.ForeignKey(
        ChargeType, 
        on_delete=models.PROTECT,
        related_name='sales_charges'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.charge_type.name} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_salecharge'
        verbose_name = "Charge de vente"
        verbose_name_plural = "Charges de vente"


class Invoice(models.Model):
    """
    Factures
    """
    reference = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='invoices')
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
    
    class Meta:
        db_table = 'gestion_api_invoice'
        verbose_name = "Facture"
        verbose_name_plural = "Factures"


class Quote(models.Model):
    """
    Devis
    """
    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT, 
        related_name='sales_quotes'
    )
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
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.reference:
            from django.db import transaction
            
            with transaction.atomic():
                year = timezone.now().year
                last_quote = Quote.objects.filter(reference__startswith=f"DEV-{year}-").select_for_update().order_by('-reference').first()
                
                if last_quote:
                    try:
                        last_number = int(last_quote.reference.split('-')[-1])
                        next_number = last_number + 1
                    except (ValueError, IndexError):
                        count = Quote.objects.filter(reference__startswith=f"DEV-{year}-").count()
                        next_number = count + 1
                else:
                    next_number = 1
                
                self.reference = f"DEV-{year}-{next_number:03d}"
                
                while Quote.objects.filter(reference=self.reference).exists():
                    next_number += 1
                    self.reference = f"DEV-{year}-{next_number:03d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference
    
    class Meta:
        db_table = 'gestion_api_quote'
        verbose_name = "Devis"
        verbose_name_plural = "Devis"


class QuoteItem(models.Model):
    """
    Éléments d'un devis
    """
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        related_name='quote_items'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except (UnitOfMeasure.DoesNotExist, AttributeError, Exception):
            unit_symbol = ""
            
        return f"{self.quote.reference} - {self.product.name} ({self.quantity} {unit_symbol})"
    
    class Meta:
        db_table = 'gestion_api_quoteitem'
        verbose_name = "Élément de devis"
        verbose_name_plural = "Éléments de devis"
