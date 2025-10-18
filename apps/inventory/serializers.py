from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from django.db.models import Max
from decimal import Decimal
from .models import (
    Product, Stock, Supply, SupplyItem, StockSupply, StockSupplyItem, StockCard,
    StockTransfer, StockTransferItem, Inventory, InventoryItem, StockReturn, StockReturnItem
)
from apps.treasury.models import Account, AccountStatement


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    unit_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'reference', 'category', 'category_name', 'unit', 'unit_name', 'purchase_price', 
                  'selling_price', 'description', 'is_raw_material', 'is_active', 'min_stock_level', 'qr_code_url']
        extra_kwargs = {
            'reference': {'required': False},
        }
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
        
    def get_unit_name(self, obj):
        return obj.unit.name if obj.unit else None
        
    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(f'/api/products/{obj.id}/qr-code/')
        return None


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    unit_name = serializers.CharField(source='product.unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='product.unit.symbol', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'quantity', 
                 'category_name', 'unit_name', 'unit_symbol', 'updated_at']


class StockSupplyItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = StockSupplyItem
        fields = ['id', 'supply', 'product', 'product_name', 'quantity', 'received_quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'product_name']
        extra_kwargs = {'supply': {'required': False}}

    def to_representation(self, instance):
        """Custom representation to ensure ID is always included"""
        data = super().to_representation(instance)
        return data


class StockSupplySerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    items = StockSupplyItemSerializer(many=True)
    reference = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = StockSupply
        fields = ['id', 'reference', 'supplier', 'supplier_name', 'zone', 'zone_name', 'date', 'status',
                  'total_amount', 'paid_amount', 'remaining_amount', 'payment_status',
                  'notes', 'created_by', 'created_by_name', 'items']
        read_only_fields = ['id', 'supplier_name', 'zone_name', 'created_by_name']
    
    def _generate_reference(self):
        """Generate a unique reference for the day."""
        today = timezone.now()
        datestr = today.strftime("%Y%m%d")
        last_ref = StockSupply.objects.filter(reference__startswith=f'SUP-{datestr}') \
            .aggregate(max_ref=Max('reference'))['max_ref']
        if last_ref:
            try:
                last_number = int(last_ref.split('-')[-1])
            except ValueError:
                last_number = 0
        else:
            last_number = 0
        return f"SUP-{datestr}-{last_number + 1:04d}"
    
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else None
    
    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone else None
    
    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        reference_value = validated_data.get('reference', '').strip()
        validated_data['reference'] = reference_value or self._generate_reference()

        supply = StockSupply.objects.create(**validated_data)

        for item_data in items_data:
            StockSupplyItem.objects.create(supply=supply, **item_data)

        supply.total_amount = supply.get_total_amount()
        supply.remaining_amount = supply.total_amount - supply.paid_amount
        supply.update_payment_status()
        supply.save(update_fields=['total_amount', 'paid_amount', 'remaining_amount', 'payment_status'])

        if supply.status == 'received':
            self._update_stock_and_create_stockcard(supply)
            self._create_account_statement(supply)

        return supply

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        status_before = instance.status

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        existing_items = {item.id: item for item in instance.items.all()}
        processed_item_ids = set()

        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id and item_id in existing_items:
                item = existing_items[item_id]
                for key, val in item_data.items():
                    if key != 'id':
                        setattr(item, key, val)
                item.save()
                processed_item_ids.add(item_id)
            else:
                if 'supply' in item_data:
                    item_data.pop('supply')
                new_item = StockSupplyItem.objects.create(supply=instance, **item_data)
                processed_item_ids.add(new_item.id)

        for item in existing_items.values():
            if item.id not in processed_item_ids:
                item.delete()

        instance.refresh_from_db()
        instance.total_amount = instance.get_total_amount()
        instance.remaining_amount = instance.total_amount - instance.paid_amount
        instance.update_payment_status()
        instance.save(update_fields=['total_amount', 'paid_amount', 'remaining_amount', 'payment_status'])

        if status_before != 'received' and instance.status == 'received':
            self._update_stock_and_create_stockcard(instance)
            self._create_account_statement(instance)

        return instance

    def _update_stock_and_create_stockcard(self, supply):
        """Handles stock quantity updates and StockCard creation"""
        for item in supply.items.all():
            qty_in = item.received_quantity or item.quantity
            stock, _ = Stock.objects.get_or_create(product=item.product, zone=supply.zone, defaults={'quantity': 0})
            stock.quantity += qty_in
            stock.save()

            StockCard.objects.create(
                product=item.product,
                zone=supply.zone,
                date=timezone.now().date(),
                transaction_type='supply',
                reference=supply.reference,
                quantity_in=qty_in,
                quantity_out=Decimal('0.00'),
                notes=f"Supply received: {supply.reference}"
            )

    def _create_account_statement(self, supply):
        """Creates account statements for supplier and company when supply is received"""
        total_amount = sum((item.received_quantity or item.quantity) * item.unit_price for item in supply.items.all())

        with transaction.atomic():
            count = AccountStatement.objects.filter(date=timezone.now().date()).count()
            reference = f"SUP-{timezone.now().strftime('%Y%m%d')}-{count + 1:04d}"
            
            supplier_account = Account.objects.get(account_type='supplier', supplier=supply.supplier)
            last_supplier_balance = AccountStatement.objects.filter(account=supplier_account).order_by('-date', '-id').first()
            supplier_previous_balance = Decimal(last_supplier_balance.balance) if last_supplier_balance else Decimal('0.00')
            new_supplier_balance = supplier_previous_balance + total_amount
            
            AccountStatement.objects.create(
                account=supplier_account,
                date=timezone.now().date(),
                transaction_type='supply',
                reference=reference,
                description=f"Supply received {supply.reference} from {supply.supplier.name}",
                credit=total_amount,
                debit=0,
                balance=new_supplier_balance
            )
            supplier_account.current_balance = new_supplier_balance
            supplier_account.save(update_fields=['current_balance'])

            company_account = Account.objects.filter(
                account_type__in=['cash', 'bank', 'internal'],
                is_active=True
            ).first()
            
            if company_account:
                last_company_balance = AccountStatement.objects.filter(account=company_account).order_by('-date', '-id').first()
                company_previous_balance = Decimal(last_company_balance.balance) if last_company_balance else Decimal('0.00')
                new_company_balance = company_previous_balance - total_amount
                
                AccountStatement.objects.create(
                    account=company_account,
                    date=timezone.now().date(),
                    transaction_type='supply',
                    reference=reference,
                    description=f"Supply payment {supply.reference} to {supply.supplier.name}",
                    debit=total_amount,
                    credit=0,
                    balance=new_company_balance
                )
                company_account.current_balance = new_company_balance
                company_account.save(update_fields=['current_balance'])


class StockCardSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()

    class Meta:
        model = StockCard
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'date', 'transaction_type', 'reference',
                  'quantity_in', 'quantity_out', 'unit_symbol', 'notes']

    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None


class StockTransferItemSerializer(serializers.ModelSerializer):
    """
    Serializer pour les éléments de transfert de stock
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = StockTransferItem
        fields = ['id', 'transfer', 'product', 'product_name', 'quantity', 'transferred_quantity', 'unit_symbol']
    
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None


class StockTransferSerializer(serializers.ModelSerializer):
    """
    Serializer pour les transferts de stock entre zones
    """
    from_zone_name = serializers.CharField(source='from_zone.name', read_only=True)
    to_zone_name = serializers.CharField(source='to_zone.name', read_only=True)
    items = StockTransferItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = ['id', 'reference', 'from_zone', 'from_zone_name', 'to_zone', 'to_zone_name', 
                  'date', 'status', 'notes', 'items', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['reference', 'created_by', 'created_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    """
    Serializer pour les éléments d'inventaire
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = ['id', 'inventory', 'product', 'product_name', 'expected_quantity', 
                  'actual_quantity', 'difference', 'notes', 'unit_symbol']
    
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None


class InventorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les inventaires de stock
    """
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    items = InventoryItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Inventory
        fields = ['id', 'reference', 'zone', 'zone_name', 'date', 'status', 'notes', 
                  'items', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['reference', 'created_by', 'created_at']


class StockReturnItemSerializer(serializers.ModelSerializer):
    """
    Serializer pour les éléments de retour de stock
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = StockReturnItem
        fields = ['id', 'stock_return', 'product', 'product_name', 'quantity', 'notes', 
                  'unit_symbol', 'created_at', 'updated_at']
    
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None


class StockReturnSerializer(serializers.ModelSerializer):
    """
    Serializer pour les retours de stock
    """
    sale_reference = serializers.CharField(source='sale.reference', read_only=True)
    items = StockReturnItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = StockReturn
        fields = ['id', 'reference', 'sale', 'sale_reference', 'date', 'status', 'status_display',
                  'reason', 'notes', 'items', 'created_by', 'created_by_username', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']
