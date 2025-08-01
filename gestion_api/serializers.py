from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from .models import (
    Product, Client, Supplier, UserProfile, Zone, Sale, SaleItem, 
    Currency, ExchangeRate, PaymentMethod, Account, PriceGroup, 
    ExpenseCategory, Expense, ClientPayment, SupplierPayment, 
    AccountTransfer, UnitOfMeasure, CashFlow, BankReconciliation, 
    BankReconciliationItem, FinancialReport, ProductCategory,
    Production, ProductionMaterial, StockSupply, StockSupplyItem, 
    StockTransfer, StockTransferItem, Inventory, InventoryItem,
    StockCard, DeliveryNote, DeliveryNoteItem, ChargeType, SaleCharge,
    Employee, ClientGroup, Invoice, Quote, QuoteItem, Stock,
    CashReceipt, AccountStatement
)

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_new_password(self, value):
        # Password validation rules
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
            
        # Check for combination of letters and numbers
        if not any(char.isdigit() for char in value) or not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must contain both letters and numbers.")
            
        return value

class PermissionSerializer(serializers.ModelSerializer):
    content_type_name = serializers.CharField(source='content_type.name', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'content_type_name', 'app_label']

class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name', 'address', 'description', 'is_active']

# SimpleUserSerializer to avoid circular imports
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        extra_kwargs = {'password': {'write_only': True}}


# GroupSerializer with minimal dependencies
class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']
        
    def create(self, validated_data):
        # Extract permission_ids from the request data
        permission_ids = self.initial_data.get('permissions', [])
        
        # Create the group without permissions first
        group = Group.objects.create(name=validated_data.get('name', ''))
        
        # Add permissions to the group using the many-to-many relationship
        if permission_ids:
            # Convert any string IDs to integers
            permission_ids = [int(id) if isinstance(id, str) and id.isdigit() else id for id in permission_ids]
            
            # Filter for existing permissions
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # Set the permissions on the group
            group.permissions.set(permissions)
        
        return group
    
    def update(self, instance, validated_data):
        # Update basic group fields
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        
        # Extract permission_ids from the request data
        permission_ids = self.initial_data.get('permissions', [])
        
        # Update permissions if provided
        if permission_ids is not None:
            # Convert any string IDs to integers
            permission_ids = [int(id) if isinstance(id, str) and id.isdigit() else id for id in permission_ids]
            
            # Filter for existing permissions
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # Set the permissions on the group
            instance.permissions.set(permissions)
            
        return instance
    
    def to_representation(self, instance):
        # Get the standard representation
        representation = super().to_representation(instance)
        return representation

# UserProfileSerializer with proper handling for the one-to-one relationship
class UserProfileSerializer(serializers.ModelSerializer):
    # Remove the group field as it doesn't exist in the model
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['id', 'role', 'zone', 'zone_name', 'is_active',
                  'user_username', 'user_email', 'user_full_name']

    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def update(self, instance, validated_data):
        # Update UserProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance

# UserSerializer that uses the updated UserProfileSerializer
class UserSerializer(serializers.ModelSerializer):
    profile_data = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    # Add these fields to accept them directly in the serializer
    role = serializers.CharField(write_only=True, required=False, allow_null=True)
    zone = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_profile_active = serializers.BooleanField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 
                  'is_staff', 'profile_data', 'permissions', 'groups', 
                  'role', 'zone', 'is_profile_active']
        read_only_fields = ['id']
        
    def get_profile_data(self, obj):
        """Get profile data with role and zone information"""
        try:
            profile = obj.profile
            if not profile:
                return None
                
            return {
                'id': profile.id,
                'role': profile.role,
                'zone': profile.zone.id if profile.zone else None,
                'zone_name': profile.zone.name if profile.zone else None,
                'is_active': profile.is_active
            }
        except Exception as e:
            print(f"Error getting profile data: {e}")
            return None
    
    def get_permissions(self, obj):
        """Get user permissions"""
        try:
            if not hasattr(obj, 'profile'):
                return []
                
            return list(obj.profile.get_all_permissions())
        except Exception as e:
            print(f"Error getting permissions: {e}")
            return []
    
    def get_groups(self, obj):
        """Get user groups"""
        try:
            # Get Django groups directly - this is the only valid source of groups
            django_groups = obj.groups.all()
            
            # This formats the groups for display in the frontend
            return [
                {
                    'id': group.id,
                    'name': group.name
                }
                for group in django_groups
            ]
        except Exception as e:
            print(f"Error getting groups: {e}")
            return []

    def create(self, validated_data):
        """Create a new user with profile data"""
        # Extract profile-related fields
        role = validated_data.pop('role', None)
        zone_id = validated_data.pop('zone', None)
        is_profile_active = validated_data.pop('is_profile_active', True)
        groups = self.initial_data.pop('groups', [])
        
        print(f"Creating user with role={role}, zone_id={zone_id}, profile_active={is_profile_active}")
        print(f"Groups being assigned: {groups}")  # Add logging for groups
        
        # Extract password separately to set it properly
        password = validated_data.pop('password', None)
        # Create the user
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        
        # Set groups if provided
        if groups:
            print(f"Setting groups for user {user.username}: {groups}")
            user.groups.set(groups)
        
        # The signal should have created the profile, but let's make sure
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"Retrieved profile for {user.username}: {profile.id}")
        except UserProfile.DoesNotExist:
            profile = UserProfile(user=user)
            print(f"Created new profile for {user.username}")
            
        # Set profile fields
        if role:
            profile.role = role
            print(f"Setting role to {role}")
            
        if zone_id:
            try:
                zone = Zone.objects.get(pk=zone_id)
                profile.zone = zone
                print(f"Setting zone to {zone.name} (id={zone.id})")
            except Zone.DoesNotExist:
                print(f"Zone with id={zone_id} not found")
                pass
                
        profile.is_active = is_profile_active
        profile.save()
        print(f"Saved profile for {user.username}: role={profile.role}, zone={profile.zone}, active={profile.is_active}")
        # Refresh user to ensure profile is attached
        user.refresh_from_db()
        return user
        
    def update(self, instance, validated_data):
        """Update an existing user and their profile"""
        # Extract profile-related fields
        role = validated_data.pop('role', None)
        zone_id = validated_data.pop('zone', None)
        is_profile_active = validated_data.pop('is_profile_active', None)
        
        # Fix: Get groups separately from request data since it might be lost during validation
        groups_data = self.context['request'].data.get('groups')
        print(f"Groups from request data: {groups_data}")
        
        # Handle password separately
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
            
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Fix: Handle groups properly
        if groups_data is not None:
            print(f"Setting groups for user {instance.username} to: {groups_data}")
            try:
                # Convert to list if it's not already
                if isinstance(groups_data, str):
                    import json
                    try:
                        groups_data = json.loads(groups_data)
                    except json.JSONDecodeError:
                        groups_data = [groups_data]
                
                # Convert any strings to integers
                group_ids = []
                for g in groups_data:
                    if isinstance(g, str) and g.isdigit():
                        group_ids.append(int(g))
                    elif isinstance(g, int):
                        group_ids.append(g)
                    elif isinstance(g, dict) and 'id' in g:
                        group_ids.append(g['id'])
                
                print(f"Processed group_ids: {group_ids}")
                
                # Clear and set groups
                instance.groups.clear()
                if group_ids:
                    instance.groups.set(group_ids)
                print(f"Groups set successfully. Current groups: {list(instance.groups.values_list('id', flat=True))}")
            except Exception as e:
                print(f"Error setting groups: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Update profile
        try:
            profile = UserProfile.objects.get(user=instance)
        except UserProfile.DoesNotExist:
            profile = UserProfile(user=instance)
            
        # Update profile fields if provided
        if role is not None:
            profile.role = role
            
        if zone_id is not None:
            try:
                zone = Zone.objects.get(pk=zone_id)
                profile.zone = zone
            except Zone.DoesNotExist:
                pass
                
        if is_profile_active is not None:
            profile.is_active = is_profile_active
            
        profile.save()
        
        # Refresh the instance to ensure we have the latest data including profile and groups
        instance.refresh_from_db()
        return instance

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    unit_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'reference', 'category', 'category_name', 'unit', 'unit_name', 'purchase_price', 
                  'selling_price', 'description', 'is_raw_material', 'is_active', 'min_stock_level', 'qr_code_url'] # Add 'min_stock_level' here
        extra_kwargs = {
            'reference': {'required': False},  # Make reference optional
        }
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
        
    def get_unit_name(self, obj):
        return obj.unit.name if obj.unit else None
        
    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(f'/api/products/{obj.id}/qr-code/')

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address', 
                  'price_group', 'account', 'is_active']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address', 
                  'account', 'is_active']

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleItem
        fields = ['id', 'sale', 'product', 'product_name', 'quantity', 'unit_price', 'discount_percentage', 'total_price']
        read_only_fields = ['id']
        extra_kwargs = {'sale': {'required': False}}  # Make sale field not required

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    # Make reference field optional
    reference = serializers.CharField(required=False)

    class Meta:
        model = Sale
        fields = ['id', 'reference', 'client', 'zone', 'date', 'status', 'payment_status', 'workflow_state',
                  'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount', 'remaining_amount',
                  'notes', 'created_by', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = Sale.objects.create(**validated_data)
        # Create SaleItem records
        for item_data in items_data:
            SaleItem.objects.create(sale=sale, **item_data)
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
                # Remove 'sale' field from item_data if it exists to prevent duplicate key
                if 'sale' in item_data:
                    item_data.pop('sale')
                SaleItem.objects.create(sale=instance, **item_data)
        # Delete items not included in the update
        for item in existing_items.values():
            item.delete()
        return instance

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code', 'symbol', 'is_base', 'is_active']

class ExchangeRateSerializer(serializers.ModelSerializer):
    from_currency_code = serializers.CharField(source='from_currency.code', read_only=True)
    to_currency_code = serializers.CharField(source='to_currency.code', read_only=True)
    
    class Meta:
        model = ExchangeRate
        fields = ['id', 'from_currency', 'from_currency_code', 'to_currency', 'to_currency_code', 
                 'rate', 'date', 'is_active']

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'description', 'is_active']

class AccountSerializer(serializers.ModelSerializer):
    currency_details = CurrencySerializer(source='currency', read_only=True)
    
    class Meta:
        model = Account
        fields = ['id', 'name', 'account_type', 'currency', 'currency_details', 
                 'initial_balance', 'current_balance', 'description', 'is_active']

class PriceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceGroup
        fields = ['id', 'name', 'discount_percentage', 'description']

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'is_active']

class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Expense
        fields = ['id', 'reference', 'category', 'category_name', 'account', 'account_name', 
                  'date', 'amount', 'description', 'payment_method', 'payment_method_name',
                  'status', 'created_by', 'created_by_name', 'created_at']

class ClientPaymentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ClientPayment
        fields = ['id', 'reference', 'client', 'client_name', 'account', 'account_name', 
                  'date', 'amount', 'payment_method', 'payment_method_name',
                  'notes', 'created_by', 'created_by_name', 'created_at']

class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = SupplierPayment
        fields = ['id', 'reference', 'supplier', 'supplier_name', 'account', 'account_name', 
                  'date', 'amount', 'payment_method', 'payment_method_name',
                  'notes', 'created_by', 'created_by_name', 'created_at']

class AccountTransferSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AccountTransfer
        fields = ['id', 'reference', 'from_account', 'from_account_name', 
                  'to_account', 'to_account_name', 'date', 'amount',
                  'exchange_rate', 'notes', 'created_by', 'created_by_name', 'created_at']

# Financial model serializers
class BankReconciliationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankReconciliationItem
        fields = ['id', 'reconciliation', 'transaction_type', 'transaction_date', 
                  'description', 'amount', 'is_reconciled', 'reference_document']

class BankReconciliationSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    items = BankReconciliationItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = BankReconciliation
        fields = ['id', 'reference', 'account', 'account_name', 'start_date', 'end_date', 
                  'bank_statement_balance', 'book_balance', 'status', 'notes', 
                  'created_by', 'created_by_name', 'created_at', 'updated_at', 'items']

class CashFlowSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = CashFlow
        fields = ['id', 'reference', 'date', 'flow_type', 'amount', 'description', 
                  'account', 'account_name', 'related_document_type', 'related_document_id', 
                  'created_by', 'created_by_name', 'created_at']

class FinancialReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = FinancialReport
        fields = ['id', 'name', 'report_type', 'parameters', 'is_active', 
                  'created_by', 'created_by_name', 'created_at', 'updated_at']

class ProductCategorySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, required=False)
    
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'created_by', 'created_by_name']
        read_only_fields = ['created_at', 'updated_at', 'created_by_name']

class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ['id', 'name', 'symbol', 'created_at', 'updated_at', 'created_by']
        read_only_fields = ['created_at', 'updated_at']
        fields = ['id', 'name', 'symbol']

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

class StockSupplyItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name

    class Meta:
        model = StockSupplyItem
        # Ensure received_quantity is included if used for partial updates later
        fields = ['id', 'supply', 'product', 'product_name', 'quantity', 'received_quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'product_name'] # Add product_name here
        extra_kwargs = {'supply': {'required': False}} # Keep this

    def to_representation(self, instance):
        """Custom representation to ensure ID is always included"""
        data = super().to_representation(instance)
        print(f"[StockSupplyItem Serializer] Serializing item {instance.id}: {data}")
        return data

class StockSupplySerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    items = StockSupplyItemSerializer(many=True)
    # Make reference optional and allow blank strings
    reference = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = StockSupply
        fields = ['id', 'reference', 'supplier', 'supplier_name', 'zone', 'zone_name', 'date', 'status', 
                  'notes', 'created_by', 'created_by_name', 'items']
        read_only_fields = ['id', 'supplier_name', 'zone_name', 'created_by_name']
    
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else None
    
    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone else None
    
    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else None
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Get the reference provided, if any
        reference_value = validated_data.get('reference')
        print(f"[Serializer Create] Initial reference value: '{reference_value}'")

        # Generate reference if it's missing or an empty string
        if not reference_value:
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Use atomic transaction or locking if high concurrency is expected
            count = StockSupply.objects.filter(reference__startswith=f'SUP-{datestr}').count()
            generated_reference = f'SUP-{datestr}-{count+1:04d}'
            validated_data['reference'] = generated_reference
            print(f"[Serializer Create] Generated reference: {generated_reference}")
        else:
            # Ensure the provided reference is not just whitespace
            if not reference_value.strip():
                 today = timezone.now()
                 datestr = today.strftime("%Y%m%d")
                 count = StockSupply.objects.filter(reference__startswith=f'SUP-{datestr}').count()
                 generated_reference = f'SUP-{datestr}-{count+1:04d}'
                 validated_data['reference'] = generated_reference
                 print(f"[Serializer Create] Provided reference was blank, generated: {generated_reference}")
            else:
                 validated_data['reference'] = reference_value.strip() # Use the stripped provided value
                 print(f"[Serializer Create] Using provided reference: {validated_data['reference']}")

        print(f"[Serializer Create] Data before StockSupply.objects.create: {validated_data}")

        try:
            # Create the supply object
            supply = StockSupply.objects.create(**validated_data)
        except Exception as e:
            print(f"[Serializer Create] Error during StockSupply.objects.create: {e}")
            print(f"[Serializer Create] Data passed to create: {validated_data}")
            raise e # Re-raise the exception

        # Create items
        for item_data in items_data:
            print(f"[StockSupply Create] Creating item: {item_data}")
            created_item = StockSupplyItem.objects.create(supply=supply, **item_data)
            print(f"[StockSupply Create] Created item with ID: {created_item.id}")

        return supply
        
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Update the supply fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        print(f"[StockSupply Update] Received {len(items_data)} items from frontend")
        print(f"[StockSupply Update] Items data: {items_data}")
        
        # Get all existing items before any changes
        existing_items = list(instance.items.all())
        print(f"[StockSupply Update] Found {len(existing_items)} existing items in database")
        
        # Track which items were updated/created
        processed_item_ids = set()
        
        for item_data in items_data:
            item_id = item_data.get('id')
            print(f"[StockSupply Update] Processing item: {item_data}")
            
            if item_id:
                # Update existing item
                try:
                    item_instance = StockSupplyItem.objects.get(id=item_id, supply=instance)
                    item_serializer = StockSupplyItemSerializer(item_instance, data=item_data, partial=True)
                    if item_serializer.is_valid():
                        item_serializer.save()
                        processed_item_ids.add(item_id)
                        print(f"[StockSupply Update] Updated existing item {item_id}")
                    else:
                        print(f"[StockSupply Update] Error updating supply item {item_id}: {item_serializer.errors}")
                except StockSupplyItem.DoesNotExist:
                    print(f"[StockSupply Update] Item {item_id} not found, will create new one")
                    # Create new item if the ID doesn't exist
                    new_item = StockSupplyItem.objects.create(supply=instance, **{k:v for k,v in item_data.items() if k != 'id'})
                    processed_item_ids.add(new_item.id)
            else:
                # Create new item (no ID provided)
                new_item = StockSupplyItem.objects.create(supply=instance, **item_data)
                processed_item_ids.add(new_item.id)
                print(f"[StockSupply Update] Created new item {new_item.id}")
        
        # Delete items that were not included in the update request
        items_to_delete = []
        for item in existing_items:
            if item.id not in processed_item_ids:
                items_to_delete.append(item.id)
                item.delete()
        
        if items_to_delete:
            print(f"[StockSupply Update] Deleted items: {items_to_delete}")
        
        instance.refresh_from_db()
        final_items = list(instance.items.all())
        print(f"[StockSupply Update] Final count: {len(final_items)} items")
        
        return instance

class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name

    class Meta:
        model = StockTransferItem
        fields = ['id', 'transfer', 'product', 'product_name', 'quantity', 'transferred_quantity']
        read_only_fields = ['id', 'product_name'] # Add product_name here
        extra_kwargs = {'transfer': {'required': False}} # Make transfer field not required for nested writes

class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True) # Allow writing items
    from_zone_name = serializers.CharField(source='from_zone.name', read_only=True)
    to_zone_name = serializers.CharField(source='to_zone.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    # Make reference field optional
    reference = serializers.CharField(required=False)

    class Meta:
        model = StockTransfer
        fields = ['id', 'reference', 'from_zone', 'from_zone_name', 'to_zone', 'to_zone_name', 'date',
                  'status', 'notes', 'created_by', 'created_by_name', 'items']
        read_only_fields = ['id', 'from_zone_name', 'to_zone_name', 'created_by_name'] # Add read-only fields

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Auto-generate reference if not provided
        if 'reference' not in validated_data:
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Get count of transfers for today to ensure uniqueness
            count = StockTransfer.objects.filter(reference__contains=f'TRA-{datestr}').count()
            validated_data['reference'] = f'TRA-{datestr}-{count+1:04d}'
        transfer = StockTransfer.objects.create(**validated_data)
        for item_data in items_data:
            # Ensure transferred_quantity defaults correctly if needed
            StockTransferItem.objects.create(transfer=transfer, **item_data)
        return transfer

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        instance = super().update(instance, validated_data)

        # Keep track of item IDs present in the update
        updated_item_ids = set()
        
        print(f"[StockTransfer Update] Received {len(items_data)} items from frontend")
        print(f"[StockTransfer Update] Items data: {items_data}")
        
        # Get all existing items before any changes
        existing_items = list(instance.items.all())
        print(f"[StockTransfer Update] Found {len(existing_items)} existing items in database")

        for item_data in items_data:
            item_id = item_data.get('id')
            print(f"[StockTransfer Update] Processing item: {item_data}")
            
            if item_id:
                # Update existing item
                try:
                    item_instance = StockTransferItem.objects.get(id=item_id, transfer=instance)
                    # Update item fields (excluding transfer)
                    item_serializer = StockTransferItemSerializer(item_instance, data=item_data, partial=True)
                    if item_serializer.is_valid():
                        item_serializer.save()
                        updated_item_ids.add(item_id)
                        print(f"[StockTransfer Update] Updated existing item {item_id}")
                    else:
                        print(f"[StockTransfer Update] Error updating transfer item {item_id}: {item_serializer.errors}")
                except StockTransferItem.DoesNotExist:
                    print(f"[StockTransfer Update] Item {item_id} not found, will create new one")
                    # Create new item if the ID doesn't exist
                    new_item = StockTransferItem.objects.create(transfer=instance, **{k:v for k,v in item_data.items() if k != 'id'})
                    updated_item_ids.add(new_item.id)
            else:
                # Create new item (no ID provided)
                new_item = StockTransferItem.objects.create(transfer=instance, **item_data)
                updated_item_ids.add(new_item.id)
                print(f"[StockTransfer Update] Created new item {new_item.id}")

        # Delete items that were not included in the update request
        items_to_delete = []
        for item in existing_items:
            if item.id not in updated_item_ids:
                items_to_delete.append(item.id)
                item.delete()
        
        if items_to_delete:
            print(f"[StockTransfer Update] Deleted items: {items_to_delete}")

        instance.refresh_from_db()
        final_items = list(instance.items.all())
        print(f"[StockTransfer Update] Final count: {len(final_items)} items")
        
        return instance

class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    # Make actual_quantity field optional during partial updates
    actual_quantity = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False  # This makes it not required during partial updates
    )

    class Meta:
        model = InventoryItem
        fields = ['id', 'inventory', 'product', 'product_name', 'expected_quantity', 'actual_quantity', 'difference', 'notes']
        read_only_fields = ['id', 'product_name', 'difference']
        extra_kwargs = {'inventory': {'required': False}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        print(f"[InventoryItemSerializer] Serializing item with ID: {data.get('id')}")
        return data

class InventorySerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True) # Allow writing items
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    # Make reference field optional and allow blank strings
    reference = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Inventory
        fields = ['id', 'reference', 'zone', 'zone_name', 'date', 'status', 'notes',
                  'created_by', 'created_by_name', 'items']
        read_only_fields = ['id', 'zone_name', 'created_by_name']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Get the reference provided, if any
        reference_value = validated_data.get('reference')
        print(f"[Inventory Serializer Create] Initial reference value: '{reference_value}'")

        # Generate reference if it's missing or an empty string
        if not reference_value:
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Get count of inventories for today to ensure uniqueness
            count = Inventory.objects.filter(reference__contains=f'INV-{datestr}').count()
            generated_reference = f'INV-{datestr}-{count+1:04d}'
            validated_data['reference'] = generated_reference
            print(f"[Inventory Serializer Create] Generated reference: {generated_reference}")
        else:
            # Ensure the provided reference is not just whitespace
            if not reference_value.strip():
                today = timezone.now()
                datestr = today.strftime("%Y%m%d")
                count = Inventory.objects.filter(reference__contains=f'INV-{datestr}').count()
                generated_reference = f'INV-{datestr}-{count+1:04d}'
                validated_data['reference'] = generated_reference
                print(f"[Inventory Serializer Create] Provided reference was blank, generated: {generated_reference}")
            else:
                validated_data['reference'] = reference_value.strip() # Use the stripped provided value
                print(f"[Inventory Serializer Create] Using provided reference: {validated_data['reference']}")
            
        inventory = Inventory.objects.create(**validated_data)
        
        print(f"Creating inventory with items: {items_data}")
        
        for item_data in items_data:
            # Handle both field name formats (counted_quantity and actual_quantity)
            # If counted_quantity is provided, use it for actual_quantity
            if 'counted_quantity' in item_data and 'actual_quantity' not in item_data:
                item_data['actual_quantity'] = item_data.pop('counted_quantity')
            
            # If we still don't have actual_quantity, set a default of 0
            if 'actual_quantity' not in item_data:
                print(f"[Inventory Create] Warning: No actual_quantity provided for item {item_data}")
                item_data['actual_quantity'] = 0
            
            # Set expected_quantity to current stock level if not provided
            if 'expected_quantity' not in item_data or item_data.get('expected_quantity', 0) == 0:
                # Get current stock for this product in this zone
                from .models import Stock
                try:
                    current_stock = Stock.objects.get(
                        product_id=item_data['product'],
                        zone=inventory.zone
                    )
                    item_data['expected_quantity'] = current_stock.quantity
                    print(f"[Inventory Create] Set expected_quantity to current stock: {current_stock.quantity}")
                except Stock.DoesNotExist:
                    # If no stock record exists, expected quantity is 0
                    item_data['expected_quantity'] = 0
                    print(f"[Inventory Create] No stock record found, expected_quantity set to 0")
                
            # Calculate difference before saving item
            expected = item_data.get('expected_quantity', 0)
            actual = item_data.get('actual_quantity', 0)
            item_data['difference'] = actual - expected
            
            print(f"[Inventory Create] Creating item: {item_data}")
            created_item = InventoryItem.objects.create(inventory=inventory, **item_data)
            print(f"[Inventory Create] Created item with ID: {created_item.id}")
        
        # Create stock card entries if inventory is completed
        self._create_stock_card_entries(inventory)
        
        return inventory

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Update the inventory fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        print(f"[Inventory Update] Received {len(items_data)} items from frontend")
        print(f"[Inventory Update] Items data: {items_data}")
        
        # Get all existing items before any changes
        existing_items = list(instance.items.all())
        print(f"[Inventory Update] Found {len(existing_items)} existing items in database")
        
        # Track which items were updated/created
        processed_item_ids = set()

        for item_data in items_data:
            # Handle both field name formats (counted_quantity and actual_quantity)
            # If counted_quantity is provided, use it for actual_quantity
            if 'counted_quantity' in item_data and 'actual_quantity' not in item_data:
                item_data['actual_quantity'] = item_data.pop('counted_quantity')
            
            # If we still don't have actual_quantity, set a default of 0
            if 'actual_quantity' not in item_data:
                print(f"[Inventory Update] Warning: No actual_quantity provided for item {item_data}")
                item_data['actual_quantity'] = 0
            
            # Set expected_quantity to current stock level if not provided (for new items)
            if ('expected_quantity' not in item_data or item_data.get('expected_quantity', 0) == 0) and not item_data.get('id'):
                # Only set expected_quantity for new items (no ID)
                from .models import Stock
                try:
                    current_stock = Stock.objects.get(
                        product_id=item_data['product'],
                        zone=instance.zone
                    )
                    item_data['expected_quantity'] = current_stock.quantity
                    print(f"[Inventory Update] Set expected_quantity for new item to current stock: {current_stock.quantity}")
                except Stock.DoesNotExist:
                    item_data['expected_quantity'] = 0
                    print(f"[Inventory Update] No stock record found for new item, expected_quantity set to 0")
            
            item_id = item_data.get('id')
            
            # For existing items, preserve expected_quantity if not provided
            if item_id and ('expected_quantity' not in item_data or item_data.get('expected_quantity') is None):
                try:
                    existing_item = InventoryItem.objects.get(id=item_id, inventory=instance)
                    item_data['expected_quantity'] = existing_item.expected_quantity
                    print(f"[Inventory Update] Preserved existing expected_quantity: {existing_item.expected_quantity}")
                except InventoryItem.DoesNotExist:
                    print(f"[Inventory Update] Existing item {item_id} not found")
            
            # Recalculate difference on update
            expected = item_data.get('expected_quantity', 0)
            actual = item_data.get('actual_quantity', 0)
            item_data['difference'] = actual - expected
            
            print(f"[Inventory Update] Processing item: {item_data}")

            if item_id:
                # Update existing item
                try:
                    item_instance = InventoryItem.objects.get(id=item_id, inventory=instance)
                    item_serializer = InventoryItemSerializer(item_instance, data=item_data, partial=True)
                    if item_serializer.is_valid():
                        item_serializer.save()
                        processed_item_ids.add(item_id)
                        print(f"[Inventory Update] Updated existing item {item_id}")
                    else:
                        print(f"[Inventory Update] Error updating inventory item {item_id}: {item_serializer.errors}")
                except InventoryItem.DoesNotExist:
                    print(f"[Inventory Update] Item {item_id} not found, will create new one")
                    # Create new item if the ID doesn't exist
                    new_item = InventoryItem.objects.create(inventory=instance, **{k:v for k,v in item_data.items() if k != 'id'})
                    processed_item_ids.add(new_item.id)
            else:
                # Create new item (no ID provided)
                new_item = InventoryItem.objects.create(inventory=instance, **item_data)
                processed_item_ids.add(new_item.id)
                print(f"[Inventory Update] Created new item {new_item.id}")
        
        # Delete items that were not included in the update request
        items_to_delete = []
        for item in existing_items:
            if item.id not in processed_item_ids:
                items_to_delete.append(item.id)
                item.delete()
        
        if items_to_delete:
            print(f"[Inventory Update] Deleted items: {items_to_delete}")
        
        instance.refresh_from_db()
        final_items = list(instance.items.all())
        print(f"[Inventory Update] Final count: {len(final_items)} items")
        
        # Create stock card entries if inventory status changed to completed
        self._create_stock_card_entries(instance)
        
        return instance

    def _create_stock_card_entries(self, inventory):
        """Create stock card entries for completed inventory adjustments"""
        if inventory.status != 'completed':
            return
            
        from .models import StockCard, Stock
        from django.db import transaction
        
        print(f"[Inventory] Creating stock card entries for inventory {inventory.reference}")
        
        # Check if stock card entries already exist for this inventory to avoid duplicates
        existing_entries = StockCard.objects.filter(
            transaction_type='inventory',
            reference=inventory.reference
        ).exists()
        
        if existing_entries:
            print(f"[Inventory] Stock card entries already exist for {inventory.reference}, skipping creation")
            return
        
        with transaction.atomic():
            for item in inventory.items.all():
                # Get or create stock entry for this product/zone
                stock, created = Stock.objects.get_or_create(
                    product=item.product,
                    zone=inventory.zone,
                    defaults={'quantity': 0}
                )
                
                # Store the original stock quantity before adjustment
                original_stock_quantity = stock.quantity
                
                # Calculate the new balance after adjustment
                new_balance = item.actual_quantity  # Set stock to actual counted quantity
                
                # Always create a stock card entry for inventory, even if difference is 0
                # This provides transparency about what was counted vs what was expected
                if item.difference != 0:
                    # For adjustments, show the adjustment amount
                    stock_card = StockCard.objects.create(
                        product=item.product,
                        zone=inventory.zone,
                        date=inventory.date,
                        transaction_type='inventory',
                        reference=inventory.reference,
                        quantity_in=item.difference if item.difference > 0 else 0,
                        quantity_out=abs(item.difference) if item.difference < 0 else 0,
                        unit_price=item.product.purchase_price or 0,
                        balance=new_balance,
                        notes=f"Inventaire: Stock système {original_stock_quantity}, comptage {item.actual_quantity}, ajustement {item.difference:+} (attendu: {item.expected_quantity})"
                    )
                else:
                    # For no difference, create an entry showing the confirmation
                    stock_card = StockCard.objects.create(
                        product=item.product,
                        zone=inventory.zone,
                        date=inventory.date,
                        transaction_type='inventory',
                        reference=inventory.reference,
                        quantity_in=0,
                        quantity_out=0,
                        unit_price=item.product.purchase_price or 0,
                        balance=new_balance,
                        notes=f"Inventaire confirmé: Stock système {original_stock_quantity}, comptage {item.actual_quantity} (attendu: {item.expected_quantity})"
                    )
                
                # Update the stock quantity to the actual counted amount
                stock.quantity = new_balance
                stock.save()
                
                print(f"[Inventory] Created stock card entry for {item.product.name}: original={original_stock_quantity}, counted={item.actual_quantity}, difference={item.difference}, new_balance={new_balance}")


class StockCardSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()

    class Meta:
        model = StockCard
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'date', 'transaction_type', 'reference',
                  'quantity_in', 'quantity_out', 'unit_price', 'balance', 'unit_symbol', 'notes']

    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None

class DeliveryNoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryNoteItem
        fields = '__all__'

class DeliveryNoteSerializer(serializers.ModelSerializer):
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

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class ClientGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientGroup
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    sale_reference = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = '__all__'

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

class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    unit_name = serializers.CharField(source='product.unit.name', read_only=True)

    class Meta:
        model = Stock
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'quantity', 
                 'category_name', 'unit_name', 'updated_at']

class CashReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashReceipt
        fields = '__all__'

class AccountStatementSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = AccountStatement
        fields = '__all__'