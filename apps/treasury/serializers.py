from rest_framework import serializers
from .models import (
    Account, Expense, ClientPayment, SupplierPayment, AccountTransfer,
    CashReceipt, SupplierCashPayment, AccountStatement
)
from apps.app_settings.serializers import CurrencySerializer


class AccountSerializer(serializers.ModelSerializer):
    currency_details = CurrencySerializer(source='currency', read_only=True)
    
    class Meta:
        model = Account
        fields = ['id', 'name', 'account_type', 'currency', 'currency_details', 
                 'initial_balance', 'current_balance', 'description', 'is_active']


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
        fields = '__all__'


class CashReceiptSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    sale_reference = serializers.CharField(source='sale.reference', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
    class Meta:
        model = CashReceipt
        fields = '__all__'


class SupplierCashPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    payment_method_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SupplierCashPayment
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
    
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else None
    
    def get_account_name(self, obj):
        return obj.account.name if obj.account else None
    
    def get_payment_method_name(self, obj):
        return obj.payment_method.name if obj.payment_method else None


class AccountStatementSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = AccountStatement
        fields = '__all__'
