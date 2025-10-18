from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from apps.app_settings.models import PriceGroup
from apps.treasury.models import Account


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
        db_table = 'gestion_api_clientgroup'
        verbose_name = "Groupe de clients"
        verbose_name_plural = "Groupes de clients"


class Client(models.Model):
    """
    Clients de l'entreprise
    """
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    price_group = models.ForeignKey(
        PriceGroup, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='partners_clients'
    )
    account = models.OneToOneField(
        Account, 
        on_delete=models.PROTECT,
        related_name='client'
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'gestion_api_client'
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Supplier(models.Model):
    """
    Fournisseurs de l'entreprise
    """
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    account = models.OneToOneField(
        Account, 
        on_delete=models.CASCADE, 
        related_name='supplier'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'gestion_api_supplier'
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"


class Employee(models.Model):
    """
    Employés de l'entreprise
    """
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, default="Général")
    email = models.EmailField(default="")
    phone = models.CharField(max_length=20)
    address = models.TextField()
    hire_date = models.DateField(default=timezone.now)
    salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)], 
        default=0
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.position}"
    
    class Meta:
        db_table = 'gestion_api_employee'
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
