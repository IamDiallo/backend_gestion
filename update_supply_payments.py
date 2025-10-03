"""
Script to update payment tracking fields for existing StockSupply records.
This should be run after the migration to populate total_amount, paid_amount, 
remaining_amount, and payment_status for all existing supplies.
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_backend.settings')
django.setup()

from gestion_api.models import StockSupply
from decimal import Decimal

def update_supply_payments():
    """Update payment tracking fields for all existing supplies"""
    supplies = StockSupply.objects.all()
    updated_count = 0
    
    print(f"Found {supplies.count()} supplies to update...")
    
    for supply in supplies:
        # Calculate total amount from items
        total_amount = supply.get_total_amount()
        
        # Update payment tracking fields
        supply.total_amount = total_amount
        supply.remaining_amount = total_amount - supply.paid_amount
        supply.update_payment_status()
        supply.save(update_fields=['total_amount', 'paid_amount', 'remaining_amount', 'payment_status'])
        
        updated_count += 1
        print(f"Updated {supply.reference}: total={total_amount}, paid={supply.paid_amount}, remaining={supply.remaining_amount}, status={supply.payment_status}")
    
    print(f"\n✅ Successfully updated {updated_count} supplies!")
    
    # Show summary
    print("\nSummary by payment status:")
    for status_code, status_label in [('unpaid', 'Non payé'), ('partially_paid', 'Partiellement payé'), ('paid', 'Payé'), ('overpaid', 'Surpayé')]:
        count = StockSupply.objects.filter(payment_status=status_code).count()
        if count > 0:
            print(f"  {status_label}: {count} supplies")
    
    # Show supplies with remaining amounts
    outstanding_supplies = StockSupply.objects.filter(remaining_amount__gt=0, status='received')
    print(f"\n📋 Outstanding supplies (received but not fully paid): {outstanding_supplies.count()}")
    for supply in outstanding_supplies[:5]:  # Show first 5
        print(f"  - {supply.reference}: {supply.supplier.name} - {supply.remaining_amount} to pay")

if __name__ == '__main__':
    print("=" * 60)
    print("Updating Supply Payment Tracking Fields")
    print("=" * 60)
    update_supply_payments()
    print("\n" + "=" * 60)
    print("Update Complete!")
    print("=" * 60)
