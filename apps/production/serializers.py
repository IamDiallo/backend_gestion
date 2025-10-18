from rest_framework import serializers
from decimal import Decimal
from django.db import transaction

from .models import Production, ProductionMaterial
from apps.inventory.models import Stock, StockCard


class ProductionMaterialSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionMaterial
        fields = ['id', 'production', 'product', 'product_name', 'quantity', 'unit_symbol']
    
    def get_unit_symbol(self, obj):
        return obj.product.unit.symbol if obj.product and obj.product.unit else ""


class ProductionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    materials = ProductionMaterialSerializer(many=True, read_only=True)
    
    class Meta:
        model = Production
        fields = ['id', 'reference', 'product', 'product_name', 'quantity', 
                  'zone', 'zone_name', 'date', 'notes', 'created_at', 'materials']
    
    def create(self, validated_data):
        """
        Create production and update stock automatically
        """
        with transaction.atomic():
            # Create the production record
            production = Production.objects.create(**validated_data)
            
            # Get or create stock for this product in this zone
            stock, created = Stock.objects.get_or_create(
                product=production.product,
                zone=production.zone,
                defaults={'quantity': Decimal('0.00')}
            )
            
            # Update stock quantity (production increases stock)
            stock.quantity += production.quantity
            stock.save()
            
            # Create StockCard entry to track this production
            StockCard.objects.create(
                product=production.product,
                zone=production.zone,
                date=production.date,
                transaction_type='production',
                reference=production.reference,
                quantity_in=production.quantity,
                quantity_out=Decimal('0.00'),
                notes=f"Production: {production.notes}" if production.notes else "Production"
            )
            
            return production
