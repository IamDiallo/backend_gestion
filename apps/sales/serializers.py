from rest_framework import serializers
from decimal import Decimal

from .models import (
    Sale, SaleItem, DeliveryNote, DeliveryNoteItem, Invoice, Quote, QuoteItem, 
    SaleCharge, ChargeType
)
from apps.inventory.models import Stock, StockCard
from apps.partners.models import Client


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleItem
        fields = ['id', 'sale', 'product', 'product_name', 'quantity', 'unit_price', 
                  'discount_percentage', 'total_price']
        read_only_fields = ['id']
        extra_kwargs = {'sale': {'required': False}}


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    reference = serializers.CharField(required=False)

    class Meta:
        model = Sale
        fields = ['id', 'reference', 'client', 'zone', 'date', 'status', 'payment_status', 
                  'workflow_state', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 
                  'paid_amount', 'remaining_amount', 'notes', 'created_by', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = Sale.objects.create(**validated_data)

        # Create SaleItem records and reduce stock
        for item_data in items_data:
            item = SaleItem.objects.create(sale=sale, **item_data)

            stock, created = Stock.objects.get_or_create(
                product=item.product,
                zone=sale.zone,
                defaults={'quantity': 0}
            )

            # Reduce stock (ensure it doesn't go negative)
            if stock.quantity < item.quantity:
                raise ValueError(f"Not enough stock for product {item.product}")
            stock.quantity -= item.quantity
            stock.save()
            
            # Create Stock Card entry for the sale
            StockCard.objects.create(
                product=item.product,
                zone=sale.zone,
                date=sale.date,
                transaction_type='sale',
                reference=sale.reference,
                quantity_in=0,
                quantity_out=item.quantity,
                notes=f"Sale: {sale.reference}"
            )

        return sale

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        # Update the sale instance
        instance = super().update(instance, validated_data)
        
        # Update or create SaleItem records
        existing_items = {item.id: item for item in instance.items.all()}
        
        # Process each item in the update data
        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items[item_id]
                for attr, value in item_data.items():
                    setattr(item, attr, value)
                item.save()
                existing_items.pop(item_id)
            else:
                # Create new item
                if 'sale' in item_data:
                    item_data.pop('sale')
                SaleItem.objects.create(sale=instance, **item_data)
        
        # Delete items not included in the update
        for item in existing_items.values():
            item.delete()
        
        return instance
    
    def delete(self, *args, **kwargs):
        """Handle safe deletion - restore stock"""
        sale = self.instance

        # Restore stock for each sale item
        for item in sale.items.all():
            stock, created = Stock.objects.get_or_create(
                product=item.product,
                zone=sale.zone,
                defaults={'quantity': 0}
            )
            stock.quantity += item.quantity
            stock.save()

        # Refund amount logic
        if sale.paid_amount > 0 and sale.client and sale.client.account:
            account = sale.client.account
            account.current_balance += sale.paid_amount
            account.save()

        # Delete the sale itself
        sale.delete()


class DeliveryNoteItemSerializer(serializers.ModelSerializer):
    """Serializer for delivery note items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryNoteItem
        fields = ['id', 'delivery_note', 'product', 'product_name', 'quantity', 
                  'unit_price', 'total_price', 'unit_symbol']
    
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None


class DeliveryNoteSerializer(serializers.ModelSerializer):
    items = DeliveryNoteItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = DeliveryNote
        fields = '__all__'


class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = '__all__'


class SaleChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleCharge
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    sale_reference = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = '__all__'

    def create(self, validated_data):
        sale = validated_data.get('sale')
        if sale and isinstance(sale, int):
            sale = Sale.objects.get(pk=sale)
        
        if sale:
            if sale.payment_status == 'paid':
                validated_data['status'] = 'paid'
                validated_data['paid_amount'] = sale.total_amount
                validated_data['balance'] = 0
            elif sale.payment_status == 'partially_paid':
                validated_data['status'] = 'partially_paid'
                validated_data['paid_amount'] = sale.paid_amount
                validated_data['balance'] = sale.total_amount - sale.paid_amount
            else:
                validated_data['status'] = 'unpaid'
                validated_data['paid_amount'] = 0
                validated_data['balance'] = sale.total_amount
        
        invoice = super().create(validated_data)
        return invoice
    
    def get_client_name(self, obj):
        try:
            return obj.sale.client.name if obj.sale and obj.sale.client else None
        except:
            return None

    def get_sale_reference(self, obj):
        try:
            return obj.sale.reference if obj.sale else None
        except:
            return None


class QuoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = QuoteItem
        fields = '__all__'


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, read_only=True)
    reference = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Quote
        fields = '__all__'
        extra_kwargs = {
            'reference': {'required': False, 'allow_blank': True}
        }
