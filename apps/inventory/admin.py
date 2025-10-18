from django.contrib import admin
from .models import (
    Product, Stock, StockSupply, StockSupplyItem, StockCard,
    StockTransfer, StockTransferItem, Inventory, InventoryItem, 
    StockReturn, StockReturnItem
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'reference', 'category', 'unit', 'selling_price', 'min_stock_level', 'is_active')
    search_fields = ('name', 'reference', 'description')
    list_filter = ('is_active', 'category', 'unit')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'reference', 'description', 'category', 'unit')
        }),
        ('Pricing', {
            'fields': ('purchase_price', 'selling_price')
        }),
        ('Stock Settings', {
            'fields': ('min_stock_level',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'zone', 'quantity', 'updated_at')
    search_fields = ('product__name', 'zone__name')
    list_filter = ('zone', 'updated_at')
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Stock should be created automatically
        return False


class StockSupplyItemInline(admin.TabularInline):
    model = StockSupplyItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'total_price')


@admin.register(StockSupply)
class StockSupplyAdmin(admin.ModelAdmin):
    list_display = ('reference', 'supplier', 'zone', 'date', 'total_amount', 'payment_status', 'status', 'created_by')
    search_fields = ('reference', 'supplier__name', 'notes')
    list_filter = ('status', 'payment_status', 'date', 'zone', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
    inlines = [StockSupplyItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('reference', 'supplier', 'zone', 'date')
        }),
        ('Financial', {
            'fields': ('total_amount', 'paid_amount', 'payment_status')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(StockSupplyItem)
class StockSupplyItemAdmin(admin.ModelAdmin):
    list_display = ('supply', 'product', 'quantity', 'unit_price', 'total_price')
    search_fields = ('supply__reference', 'product__name')
    list_filter = ('supply__date',)


@admin.register(StockCard)
class StockCardAdmin(admin.ModelAdmin):
    list_display = ('product', 'zone', 'date', 'transaction_type', 'reference', 'quantity_in', 'quantity_out')
    search_fields = ('product__name', 'zone__name', 'reference', 'notes')
    list_filter = ('transaction_type', 'date', 'zone')
    date_hierarchy = 'date'
    readonly_fields = ('date',)
    
    def has_add_permission(self, request):
        # Stock cards should be created automatically
        return False


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1
    fields = ('product', 'quantity', 'transferred_quantity')
    readonly_fields = ('transferred_quantity',)


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('reference', 'from_zone', 'to_zone', 'date', 'status', 'created_by', 'created_at')
    search_fields = ('reference', 'notes')
    list_filter = ('status', 'date', 'from_zone', 'to_zone', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('reference', 'created_by', 'created_at')
    inlines = [StockTransferItemInline]
    fieldsets = (
        ('Transfer Information', {
            'fields': ('reference', 'from_zone', 'to_zone', 'date', 'status')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(StockTransferItem)
class StockTransferItemAdmin(admin.ModelAdmin):
    list_display = ('transfer', 'product', 'quantity', 'transferred_quantity')
    search_fields = ('transfer__reference', 'product__name')
    list_filter = ('transfer__date',)
    readonly_fields = ('transferred_quantity',)


class InventoryItemInline(admin.TabularInline):
    model = InventoryItem
    extra = 1
    fields = ('product', 'expected_quantity', 'actual_quantity', 'difference', 'notes')
    readonly_fields = ('difference',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'zone', 'date', 'status', 'created_by', 'created_at')
    search_fields = ('reference', 'notes')
    list_filter = ('status', 'date', 'zone', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('reference', 'created_by', 'created_at')
    inlines = [InventoryItemInline]
    fieldsets = (
        ('Inventory Information', {
            'fields': ('reference', 'zone', 'date', 'status')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'product', 'expected_quantity', 'actual_quantity', 'difference')
    search_fields = ('inventory__reference', 'product__name')
    list_filter = ('inventory__date',)
    readonly_fields = ('difference',)


class StockReturnItemInline(admin.TabularInline):
    model = StockReturnItem
    extra = 1
    fields = ('product', 'quantity', 'notes')


@admin.register(StockReturn)
class StockReturnAdmin(admin.ModelAdmin):
    list_display = ('reference', 'sale', 'date', 'status', 'created_by', 'created_at')
    search_fields = ('reference', 'reason', 'notes')
    list_filter = ('status', 'date', 'created_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    inlines = [StockReturnItemInline]
    fieldsets = (
        ('Return Information', {
            'fields': ('reference', 'sale', 'date', 'status')
        }),
        ('Details', {
            'fields': ('reason', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(StockReturnItem)
class StockReturnItemAdmin(admin.ModelAdmin):
    list_display = ('stock_return', 'product', 'quantity', 'created_at')
    search_fields = ('stock_return__reference', 'product__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
