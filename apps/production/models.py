from django.db import models
from django.core.validators import MinValueValidator
from apps.app_settings.models import UnitOfMeasure
from apps.inventory.models import Product
from apps.core.models import Zone


class Production(models.Model):
    """
    Ordres de production
    """
    reference = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='productions'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.CASCADE,
        related_name='productions'
    )
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Production {self.reference} - {self.product.name}"
    
    class Meta:
        db_table = 'gestion_api_production'
        verbose_name = "Production"
        verbose_name_plural = "Productions"


class ProductionMaterial(models.Model):
    """
    Matières premières utilisées pour la production
    """
    production = models.ForeignKey(
        Production, 
        on_delete=models.CASCADE, 
        related_name='materials'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='production_materials'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        try:
            unit_obj = UnitOfMeasure.objects.get(id=self.product.unit.id)
            unit_symbol = unit_obj.symbol
        except UnitOfMeasure.DoesNotExist:
            unit_symbol = ""
        except Exception:
            unit_symbol = "units"
            
        return f"{self.product.name} - {self.quantity} {unit_symbol}"
    
    class Meta:
        db_table = 'gestion_api_productionmaterial'
        verbose_name = "Matière première utilisée"
        verbose_name_plural = "Matières premières utilisées"
