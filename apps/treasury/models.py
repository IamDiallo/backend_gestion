from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from apps.app_settings.models import Currency, ExpenseCategory, PaymentMethod


class Account(models.Model):
    """
    Comptes financiers (bancaires, caisses, comptes clients/fournisseurs)
    """
    ACCOUNT_TYPES = [
        ('internal', 'Compte Interne'),
        ('bank', 'Compte Bancaire'),
        ('cash', 'Caisse'),
        ('client', 'Compte Client'),
        ('supplier', 'Compte Fournisseur'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.PROTECT,
        related_name='treasury_accounts'
    )
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"
    
    class Meta:
        db_table = 'gestion_api_account'
        verbose_name = "Compte"
        verbose_name_plural = "Comptes"


class Expense(models.Model):
    """
    Dépenses de l'entreprise
    """
    reference = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.PROTECT,
        related_name='treasury_expenses'
    )
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    description = models.TextField()
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT,
        related_name='treasury_expenses'
    )
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé')
    ])
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_expenses_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dépense {self.reference} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_expense'
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"


class ClientPayment(models.Model):
    """
    Règlement client
    """
    reference = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(
        'partners.Client', 
        on_delete=models.PROTECT,
        related_name='treasury_payments'
    )
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT,
        related_name='client_payments'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT,
        related_name='treasury_client_payments'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_client_payments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Règlement {self.reference} - {self.client.name} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_clientpayment'
        verbose_name = "Règlement client"
        verbose_name_plural = "Règlements clients"


class SupplierPayment(models.Model):
    """
    Règlement fournisseur
    """
    reference = models.CharField(max_length=20, unique=True)
    supplier = models.ForeignKey(
        'partners.Supplier', 
        on_delete=models.PROTECT,
        related_name='treasury_payments'
    )
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT,
        related_name='supplier_payments'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT,
        related_name='treasury_supplier_payments'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_supplier_payments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Règlement {self.reference} - {self.supplier.name} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_supplierpayment'
        verbose_name = "Règlement fournisseur"
        verbose_name_plural = "Règlements fournisseurs"


class AccountTransfer(models.Model):
    """
    Virement entre comptes
    """
    reference = models.CharField(max_length=20, unique=True)
    from_account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT, 
        related_name='transfers_from', 
        null=True
    )
    to_account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT, 
        related_name='transfers_to', 
        null=True
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[MinValueValidator(0)], 
        default=1
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_transfers_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Virement {self.reference} - {self.from_account.name} → {self.to_account.name} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_accounttransfer'
        verbose_name = "Virement"
        verbose_name_plural = "Virements"


class CashReceipt(models.Model):
    """
    Encaissement
    """
    reference = models.CharField(max_length=20, unique=True)
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT, 
        null=True,
        related_name='cash_receipts'
    )
    sale = models.ForeignKey(
        'sales.Sale',  # Now referencing migrated sales app
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='receipts'
    )
    client = models.ForeignKey(
        'partners.Client', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='treasury_cash_receipts'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    allocated_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)], 
        default=0
    )
    description = models.TextField(default="")
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT, 
        null=True,
        related_name='treasury_cash_receipts'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_cash_receipts_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Encaissement {self.reference} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_cashreceipt'
        verbose_name = "Encaissement"
        verbose_name_plural = "Encaissements"


class SupplierCashPayment(models.Model):
    """
    Paiement aux fournisseurs (décaissement)
    """
    reference = models.CharField(max_length=50, unique=True)
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT, 
        null=True,
        related_name='supplier_cash_payments'
    )
    supply = models.ForeignKey(
        'inventory.StockSupply',  # Updated to new inventory app location
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='payments'
    )
    supplier = models.ForeignKey(
        'partners.Supplier', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='treasury_cash_payments'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    allocated_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(0)], 
        default=0
    )
    description = models.TextField(default="")
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.PROTECT, 
        null=True,
        related_name='treasury_supplier_cash_payments'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='treasury_supplier_cash_payments_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Paiement fournisseur {self.reference} - {self.amount}"
    
    class Meta:
        db_table = 'gestion_api_suppliercashpayment'
        verbose_name = "Paiement fournisseur"
        verbose_name_plural = "Paiements fournisseurs"


class AccountStatement(models.Model):
    """
    Relevé de compte pour suivre les mouvements
    """
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT,
        related_name='statements'
    )
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
    reference = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f"Mouvement {self.account.name} - {self.date} - {self.get_transaction_type_display()}"
    
    class Meta:
        db_table = 'gestion_api_accountstatement'
        verbose_name = "Mouvement de compte"
        verbose_name_plural = "Mouvements de compte"
        ordering = ['account', '-date']
