#!/usr/bin/env python
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_backend.settings')
django.setup()

from gestion_api.models import Product, ProductCategory, UnitOfMeasure
from gestion_api.serializers import ProductSerializer

def test_product_serializer():
    print("=== Testing Product Serializer ===")
    
    # Get required objects
    category = ProductCategory.objects.first()
    unit = UnitOfMeasure.objects.first()
    
    if not category or not unit:
        print("Missing category or unit for testing")
        return
    
    # Test data with min_stock_level
    product_data = {
        'name': 'Test Product Serializer',
        'category': category.id,
        'unit': unit.id,
        'purchase_price': 100.00,
        'selling_price': 150.00,
        'min_stock_level': 30,  # This should be saved
        'is_raw_material': False,
        'is_active': True,
        'description': 'Test product for serializer'
    }
    
    # Create product using serializer
    serializer = ProductSerializer(data=product_data)
    
    if serializer.is_valid():
        product = serializer.save()
        print(f"✅ Product created successfully: {product.name}")
        print(f"min_stock_level in database: {product.min_stock_level}")
        
        # Test reading the product back
        read_serializer = ProductSerializer(product)
        print(f"min_stock_level in serialized data: {read_serializer.data.get('min_stock_level')}")
        
        if product.min_stock_level == 30:
            print("✅ min_stock_level saved and retrieved correctly!")
        else:
            print("❌ min_stock_level not saved correctly!")
            
        # Test updating min_stock_level
        update_data = {'min_stock_level': 50}
        update_serializer = ProductSerializer(product, data=update_data, partial=True)
        
        if update_serializer.is_valid():
            updated_product = update_serializer.save()
            print(f"Updated min_stock_level: {updated_product.min_stock_level}")
            
            if updated_product.min_stock_level == 50:
                print("✅ min_stock_level updated correctly!")
            else:
                print("❌ min_stock_level not updated correctly!")
        else:
            print(f"Update serializer errors: {update_serializer.errors}")
            
    else:
        print(f"Serializer errors: {serializer.errors}")

if __name__ == "__main__":
    test_product_serializer()
