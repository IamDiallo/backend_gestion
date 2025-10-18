from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class UserProfile(models.Model):
    """User profile with role and permissions"""
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('consultant', 'Consultant'),
        ('supervisor', 'Supervisor'),
        ('commercial', 'Commercial'),
        ('cashier', 'Cashier'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='core_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, related_name='core_users')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    class Meta:
        db_table = 'gestion_api_userprofile'  # Point to existing table

    def has_permission(self, permission_code):
        """Check if user has a specific permission through Django's permission system"""
        # Admin users have all permissions
        if self.role == 'admin':
            return True
            
        # Check app_label and codename from the permission code
        if '.' in permission_code:
            app_label, codename = permission_code.split('.')
            return self.user.has_perm(f"{app_label}.{codename}")
        else:
            return self.user.has_perm(permission_code)
    
    def get_all_permissions(self):
        """Get all permissions for this user, including from group"""
        # Start with direct user permissions
        permissions = set()
        
        # Add all direct permissions assigned to the user
        for perm in self.user.user_permissions.all():
            permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
        
        # Add permissions from Django groups
        for group in self.user.groups.all():
            for perm in group.permissions.all():
                permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
                
        return permissions

    class Meta:
        db_table = 'gestion_api_userprofile'  # Point to existing table
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class Zone(models.Model):
    """Warehouse/Store location"""
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='core_zones_created')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'gestion_api_zone'  # Point to existing table
        verbose_name = "Zone/Magasin"
        verbose_name_plural = "Zones/Magasins"
        # TEMPORARILY comment out db_table to avoid conflict during transition
        # db_table = 'gestion_api_zone'
