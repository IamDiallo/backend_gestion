from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, Zone, Product, Client, Supplier, Sale, SaleItem, 
    Production, ProductionMaterial, StockSupply, StockSupplyItem, 
    StockTransfer, StockTransferItem, Inventory, InventoryItem, 
    StockCard, DeliveryNote, DeliveryNoteItem, ChargeType, SaleCharge, 
    ClientGroup, Employee, Invoice, Quote, QuoteItem,
    Permission
)

# Register your models here
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

# Extend User admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    
    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return '-'
    get_role.short_description = 'Role'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(Zone)
admin.site.register(Product)
admin.site.register(Client)
admin.site.register(Supplier)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(Production)
admin.site.register(ProductionMaterial)
admin.site.register(StockSupply)
admin.site.register(StockSupplyItem)
admin.site.register(StockTransfer)
admin.site.register(StockTransferItem)
admin.site.register(Inventory)
admin.site.register(InventoryItem)
admin.site.register(StockCard)
admin.site.register(DeliveryNote)
admin.site.register(DeliveryNoteItem)
admin.site.register(ChargeType)
admin.site.register(SaleCharge)
admin.site.register(ClientGroup)
admin.site.register(Employee)
admin.site.register(Invoice)
admin.site.register(Quote)
admin.site.register(QuoteItem)
admin.site.register(Permission)


# DO NOT register Group here - it's already registered by Django admin
