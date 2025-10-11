#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add StockCard creation to Sale serializer
"""

# Read the file
with open('gestion_api/serializers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define what to find and replace
old_code = """            stock.quantity -= item.quantity
            stock.save()

        return sale"""

new_code = """            stock.quantity -= item.quantity
            stock.save()
            
            # Create Stock Card entry for the sale
            StockCard.objects.create(
                product=item.product,
                zone=sale.zone,
                date=sale.date,
                transaction_type='sale',
                reference=sale.reference,
                quantity_in=0,
                quantity_out=item.quantity,
                notes=f"Sale: {sale.reference}"
            )

        return sale"""

# Replace
if old_code in content:
    content = content.replace(old_code, new_code)
    # Write back
    with open('gestion_api/serializers.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Successfully added StockCard creation to Sale serializer")
else:
    print("❌ Could not find the code to replace")
    print("Searching for parts...")
    if "stock.save()" in content:
        print("  ✓ Found 'stock.save()'")
    if "return sale" in content:
        print("  ✓ Found 'return sale'")
