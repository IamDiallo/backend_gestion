"""
Signals for inventory app
Handles cache invalidation and other post-save/delete operations
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product


@receiver(post_save, sender=Product)
def invalidate_product_qr_cache(sender, instance, **kwargs):
    """
    Invalidate QR code cache when product is updated
    This ensures that if the reference changes, a new QR code is generated
    """
    cache_key = f'qr_code_product_{instance.id}_{instance.reference}'
    cache.delete(cache_key)
    
    # Also delete any old cache keys that might exist (in case reference changed)
    # Pattern: qr_code_product_{id}_*
    # Note: Django's cache backend may not support pattern-based deletion
    # This is a best-effort cleanup
    

@receiver(post_delete, sender=Product)
def cleanup_product_qr_cache(sender, instance, **kwargs):
    """
    Clean up QR code cache when product is deleted
    """
    cache_key = f'qr_code_product_{instance.id}_{instance.reference}'
    cache.delete(cache_key)
