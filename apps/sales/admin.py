from django.contrib import admin
from .models import (
    Sale, SaleItem, DeliveryNote, Invoice, 
    Quote, QuoteItem, SaleCharge
)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'discount_percentage', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('reference', 'client', 'zone', 'date', 'total_amount', 'paid_amount', 'payment_status', 'status')
    search_fields = ('reference', 'client__name', 'notes')
    list_filter = ('status', 'payment_status', 'workflow_state', 'date', 'zone')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
    inlines = [SaleItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('reference', 'client', 'zone', 'date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'paid_amount', 'remaining_amount')
        }),
        ('Status', {
            'fields': ('status', 'payment_status', 'workflow_state')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_by', 'created_at')
        }),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price', 'discount_percentage', 'total_price')
    search_fields = ('sale__reference', 'product__name')
    list_filter = ('sale__date',)


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ('reference', 'client', 'date', 'status')
    search_fields = ('reference', 'client__name')
    list_filter = ('status', 'date')
    date_hierarchy = 'date'


@admin.register(SaleCharge)
class SaleChargeAdmin(admin.ModelAdmin):
    list_display = ('sale', 'charge_type', 'amount', 'description')
    search_fields = ('sale__reference', 'charge_type__name', 'description')
    list_filter = ('charge_type', 'sale__date')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('reference', 'sale', 'date', 'amount', 'paid_amount', 'balance', 'status')
    search_fields = ('reference', 'sale__reference')
    list_filter = ('status', 'date')
    date_hierarchy = 'date'
    fieldsets = (
        ('Basic Information', {
            'fields': ('reference', 'sale', 'date')
        }),
        ('Financial Details', {
            'fields': ('amount', 'paid_amount', 'balance')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
    )


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'discount_percentage', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('reference', 'client', 'date', 'total_amount', 'expiry_date', 'is_converted', 'status')
    search_fields = ('reference', 'client__name', 'notes')
    list_filter = ('status', 'is_converted', 'date', 'expiry_date')
    date_hierarchy = 'date'
    inlines = [QuoteItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('reference', 'client', 'date', 'expiry_date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        ('Status', {
            'fields': ('status', 'is_converted')
        }),
        ('Additional Info', {
            'fields': ('notes',)
        }),
    )


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ('quote', 'product', 'quantity', 'unit_price', 'discount_percentage', 'total_price')
    search_fields = ('quote__reference', 'product__name')
    list_filter = ('quote__date',)
