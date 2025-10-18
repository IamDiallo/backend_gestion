from django.contrib import admin
from .models import (
    Account, AccountStatement, CashReceipt, Expense, 
    ClientPayment, SupplierPayment, SupplierCashPayment
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'currency', 'current_balance', 'is_active')
    search_fields = ('name',)
    list_filter = ('account_type', 'currency', 'is_active')
    readonly_fields = ('current_balance',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'account_type', 'currency')
        }),
        ('Balance', {
            'fields': ('initial_balance', 'current_balance')
        }),
        ('Relationships', {
            'fields': ('client', 'supplier')
        }),
        ('Additional Info', {
            'fields': ('description', 'is_active')
        }),
    )


@admin.register(AccountStatement)
class AccountStatementAdmin(admin.ModelAdmin):
    list_display = ('account', 'date', 'transaction_type', 'reference', 'credit', 'debit', 'balance')
    search_fields = ('account__name', 'reference', 'description')
    list_filter = ('transaction_type', 'date', 'account')
    date_hierarchy = 'date'
    readonly_fields = ('balance',)
    
    def has_add_permission(self, request):
        # Account statements should be created automatically
        return False


@admin.register(CashReceipt)
class CashReceiptAdmin(admin.ModelAdmin):
    list_display = ('reference', 'client', 'account', 'date', 'amount', 'allocated_amount', 'created_by')
    search_fields = ('reference', 'client__name', 'description')
    list_filter = ('date', 'account', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('reference', 'category', 'account', 'date', 'amount', 'status', 'created_by')
    search_fields = ('reference', 'description')
    list_filter = ('status', 'category', 'date', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(ClientPayment)
class ClientPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'client', 'account', 'date', 'amount', 'payment_method', 'created_by')
    search_fields = ('reference', 'client__name', 'notes')
    list_filter = ('date', 'payment_method', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'supplier', 'account', 'date', 'amount', 'payment_method', 'created_by')
    search_fields = ('reference', 'supplier__name', 'notes')
    list_filter = ('date', 'payment_method', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(SupplierCashPayment)
class SupplierCashPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'supplier', 'account', 'date', 'amount', 'payment_method')
    search_fields = ('reference', 'supplier__name', 'description')
    list_filter = ('date', 'payment_method', 'supplier')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
