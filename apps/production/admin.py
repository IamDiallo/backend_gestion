from django.contrib import admin
from .models import Production, ProductionMaterial


class ProductionMaterialInline(admin.TabularInline):
    model = ProductionMaterial
    extra = 1
    fields = ('product', 'quantity')


@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'product', 'quantity', 'zone', 'date', 'created_at')
    search_fields = ('reference', 'product__name', 'notes')
    list_filter = ('date', 'zone', 'created_at')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
    inlines = [ProductionMaterialInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('reference', 'product', 'quantity', 'zone', 'date')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at')
        }),
    )


@admin.register(ProductionMaterial)
class ProductionMaterialAdmin(admin.ModelAdmin):
    list_display = ('production', 'product', 'quantity')
    search_fields = ('production__reference', 'product__name')
    list_filter = ('production__date',)
