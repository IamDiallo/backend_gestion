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
    unit_symbol = serializers.SerializerMethodField()

    class Meta:
        model = StockSupplyItem
        fields = ['id', 'supply', 'product', 'product_name', 'quantity', 'received_quantity', 'unit_price', 'total_price', 'unit_symbol']
        read_only_fields = ['id', 'product_name', 'unit_symbol']
        extra_kwargs = {'supply': {'required': False}}
    
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None

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
        read_only_fields = ['transfer']
    
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
    items = StockTransferItemSerializer(many=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = ['id', 'reference', 'from_zone', 'from_zone_name', 'to_zone', 'to_zone_name', 
                  'date', 'status', 'notes', 'items', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['reference', 'created_by', 'created_at']
    
    def create(self, validated_data):
        """Create transfer with items"""
        items_data = validated_data.pop('items')
        
        # Generate reference if not provided
        if not validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            count = StockTransfer.objects.filter(reference__startswith=f'TRF-{datestr}').count()
            validated_data['reference'] = f'TRF-{datestr}-{count+1:04d}'
        
        transfer = StockTransfer.objects.create(**validated_data)
        
        # Create items
        for item_data in items_data:
            # Remove read-only fields that might be sent by frontend
            item_data.pop('transfer', None)
            item_data.pop('id', None)
            StockTransferItem.objects.create(transfer=transfer, **item_data)
        
        # Update stock if status is completed
        if transfer.status == 'completed':
            self._update_stock_and_create_stockcard(transfer)
        
        return transfer
    
    def update(self, instance, validated_data):
        """Update transfer with items"""
        items_data = validated_data.pop('items', [])
        status_before = instance.status
        
        # Update transfer fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items
        existing_items = {item.id: item for item in instance.items.all()}
        processed_item_ids = set()
        
        for item_data in items_data:
            item_id = item_data.get('id')
            # Remove read-only fields
            item_data.pop('transfer', None)
            
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items[item_id]
                for key, val in item_data.items():
                    if key != 'id':
                        setattr(item, key, val)
                item.save()
                processed_item_ids.add(item_id)
            else:
                # Create new item - remove id if present
                item_data.pop('id', None)
                new_item = StockTransferItem.objects.create(transfer=instance, **item_data)
                processed_item_ids.add(new_item.id)
        
        # Delete items that are no longer present
        for item in existing_items.values():
            if item.id not in processed_item_ids:
                item.delete()
        
        # Update stock if status changed to completed
        if status_before != 'completed' and instance.status == 'completed':
            self._update_stock_and_create_stockcard(instance)
        
        return instance
    
    def _update_stock_and_create_stockcard(self, transfer):
        """Update stock quantities and create stock cards for completed transfers"""
        from decimal import Decimal
        
        for item in transfer.items.all():
            quantity = item.transferred_quantity if item.transferred_quantity > 0 else item.quantity
            
            # Decrease stock in source zone
            source_stock, _ = Stock.objects.get_or_create(
                product=item.product, 
                zone=transfer.from_zone, 
                defaults={'quantity': 0}
            )
            source_stock.quantity -= quantity
            source_stock.save()
            
            # Increase stock in destination zone
            dest_stock, _ = Stock.objects.get_or_create(
                product=item.product, 
                zone=transfer.to_zone, 
                defaults={'quantity': 0}
            )
            dest_stock.quantity += quantity
            dest_stock.save()
            
            # Create stock card for source zone (out)
            StockCard.objects.create(
                product=item.product,
                zone=transfer.from_zone,
                date=transfer.date,
                transaction_type='transfer_out',
                reference=transfer.reference,
                quantity_in=Decimal('0.00'),
                quantity_out=quantity,
                notes=f"Transfer to {transfer.to_zone.name}: {transfer.reference}"
            )
            
            # Create stock card for destination zone (in)
            StockCard.objects.create(
                product=item.product,
                zone=transfer.to_zone,
                date=transfer.date,
                transaction_type='transfer_in',
                reference=transfer.reference,
                quantity_in=quantity,
                quantity_out=Decimal('0.00'),
                notes=f"Transfer from {transfer.from_zone.name}: {transfer.reference}"
            )


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
        read_only_fields = ['inventory', 'difference']
    
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
    items = InventoryItemSerializer(many=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Inventory
        fields = ['id', 'reference', 'zone', 'zone_name', 'date', 'status', 'notes', 
                  'items', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['reference', 'created_by', 'created_at']
    
    def create(self, validated_data):
        """Create inventory with items"""
        items_data = validated_data.pop('items')
        
        # Generate reference if not provided
        if not validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            count = Inventory.objects.filter(reference__startswith=f'INV-{datestr}').count()
            validated_data['reference'] = f'INV-{datestr}-{count+1:04d}'
        
        inventory = Inventory.objects.create(**validated_data)
        
        # Create items
        for item_data in items_data:
            # Remove read-only fields that might be sent by frontend
            item_data.pop('inventory', None)
            item_data.pop('id', None)
            item_data.pop('difference', None)
            
            # Auto-fill expected_quantity with current stock if not provided or is 0
            if 'expected_quantity' not in item_data or item_data.get('expected_quantity') == 0:
                try:
                    stock = Stock.objects.get(
                        product=item_data['product'],
                        zone=inventory.zone
                    )
                    item_data['expected_quantity'] = stock.quantity
                except Stock.DoesNotExist:
                    # If no stock exists, expected quantity is 0
                    item_data['expected_quantity'] = 0
            
            InventoryItem.objects.create(inventory=inventory, **item_data)
        
        # Update stock if status is completed
        if inventory.status == 'completed':
            self._update_stock_and_create_stockcard(inventory)
        
        return inventory
    
    def update(self, instance, validated_data):
        """Update inventory with items"""
        items_data = validated_data.pop('items', [])
        status_before = instance.status
        
        # Update inventory fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items
        existing_items = {item.id: item for item in instance.items.all()}
        processed_item_ids = set()
        
        for item_data in items_data:
            item_id = item_data.get('id')
            # Remove read-only fields
            item_data.pop('inventory', None)
            item_data.pop('difference', None)
            
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items[item_id]
                for key, val in item_data.items():
                    if key != 'id':
                        setattr(item, key, val)
                item.save()
                processed_item_ids.add(item_id)
            else:
                # Create new item - remove id if present
                item_data.pop('id', None)
                
                # Auto-fill expected_quantity with current stock if not provided or is 0
                if 'expected_quantity' not in item_data or item_data.get('expected_quantity') == 0:
                    try:
                        stock = Stock.objects.get(
                            product=item_data['product'],
                            zone=instance.zone
                        )
                        item_data['expected_quantity'] = stock.quantity
                    except Stock.DoesNotExist:
                        # If no stock exists, expected quantity is 0
                        item_data['expected_quantity'] = 0
                
                new_item = InventoryItem.objects.create(inventory=instance, **item_data)
                processed_item_ids.add(new_item.id)
        
        # Delete items that are no longer present
        for item in existing_items.values():
            if item.id not in processed_item_ids:
                item.delete()
        
        # Update stock if status changed to completed
        if status_before != 'completed' and instance.status == 'completed':
            self._update_stock_and_create_stockcard(instance)
        
        return instance
    
    def _update_stock_and_create_stockcard(self, inventory):
        """Update stock quantities and create stock cards for completed inventories"""
        from decimal import Decimal
        
        for item in inventory.items.all():
            # Calculate difference
            difference = item.actual_quantity - item.expected_quantity
            item.difference = difference
            item.save()  # Don't use update_fields to avoid force_update issues with new items
            
            # ALWAYS update stock with actual_quantity when inventory is completed
            # This is the core principle of physical inventory - we trust the physical count
            stock, _ = Stock.objects.get_or_create(
                product=item.product,
                zone=inventory.zone,
                defaults={'quantity': 0}
            )
            stock.quantity = item.actual_quantity
            stock.save()
            
            # Create stock card only if there's a difference
            if difference != 0:
                if difference > 0:
                    # Surplus
                    StockCard.objects.create(
                        product=item.product,
                        zone=inventory.zone,
                        date=inventory.date,
                        transaction_type='Sortie Adjustment Inventaire',
                        reference=inventory.reference,
                        quantity_in=difference,
                        quantity_out=Decimal('0.00'),
                        notes=f"Inventory adjustment (surplus): {inventory.reference}"
                    )
                else:
                    # Shortage
                    StockCard.objects.create(
                        product=item.product,
                        zone=inventory.zone,
                        date=inventory.date,
                        transaction_type='Entrée Adjustment Inventaire',
                        reference=inventory.reference,
                        quantity_in=Decimal('0.00'),
                        quantity_out=abs(difference),
                        notes=f"Inventory adjustment (shortage): {inventory.reference}"
                    )


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
