from django.contrib import admin
from .models import Client, ClientGroup, Supplier, Employee


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'price_group', 'is_active')
    search_fields = ('name', 'contact_person', 'phone', 'email')
    list_filter = ('is_active', 'price_group')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Business Settings', {
            'fields': ('price_group', 'account')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    search_fields = ('name', 'contact_person', 'phone', 'email')
    list_filter = ('is_active',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Account', {
            'fields': ('account',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'phone', 'email', 'hire_date', 'is_active')
    search_fields = ('name', 'position', 'phone', 'email')
    list_filter = ('is_active', 'hire_date', 'position')
    date_hierarchy = 'hire_date'
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'phone', 'email', 'address')
        }),
        ('Employment Details', {
            'fields': ('position', 'hire_date', 'salary')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
