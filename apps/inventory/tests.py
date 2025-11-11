"""
Tests for Inventory app - Product, Stock, StockCard, StockTransfer
"""
import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from datetime import date

from apps.inventory.models import (
    Product, Stock, StockCard, StockSupply, StockSupplyItem,
    StockTransfer, StockTransferItem, Inventory, InventoryItem
)


# ============= Product Model Tests =============

@pytest.mark.django_db
class TestProductModel:
    """Test Product model"""
    
    def test_product_creation(self, product):
        """Test creating a product"""
        assert product.id is not None
        assert product.name == "Test Product"
        assert product.reference is not None
        assert product.is_active is True
    
    def test_product_reference_generation(self, db, product_category, unit_of_measure):
        """Test automatic reference generation"""
        product1 = Product.objects.create(
            name="Product 1",
            category=product_category,
            unit=unit_of_measure,
            purchase_price=Decimal('50.00'),
            selling_price=Decimal('75.00')
        )
        product2 = Product.objects.create(
            name="Product 2",
            category=product_category,
            unit=unit_of_measure,
            purchase_price=Decimal('60.00'),
            selling_price=Decimal('90.00')
        )
        
        assert product1.reference is not None
        assert product2.reference is not None
        assert product1.reference != product2.reference
    
    def test_product_str_representation(self, product):
        """Test string representation"""
        assert str(product) == "Test Product"
    
    def test_product_price_margins(self, product):
        """Test product pricing"""
        assert product.selling_price > product.purchase_price
        margin = product.selling_price - product.purchase_price
        assert margin == Decimal('50.00')


# ============= Stock Model Tests =============

@pytest.mark.django_db
class TestStockModel:
    """Test Stock model"""
    
    def test_stock_creation(self, stock):
        """Test creating stock"""
        assert stock.id is not None
        assert stock.quantity == Decimal('100.00')
        assert stock.product is not None
        assert stock.zone is not None
    
    def test_stock_unique_constraint(self, db, product, zone):
        """Test unique constraint on product+zone"""
        Stock.objects.create(
            product=product,
            zone=zone,
            quantity=Decimal('50.00')
        )
        
        # Creating another stock for same product+zone should raise error
        with pytest.raises(Exception):
            Stock.objects.create(
                product=product,
                zone=zone,
                quantity=Decimal('30.00')
            )
    
    def test_stock_update(self, stock):
        """Test updating stock quantity"""
        original_quantity = stock.quantity
        stock.quantity += Decimal('50.00')
        stock.save()
        stock.refresh_from_db()
        assert stock.quantity == original_quantity + Decimal('50.00')
    
    def test_stock_str_representation(self, stock, unit_of_measure):
        """Test string representation"""
        stock_str = str(stock)
        assert stock.product.name in stock_str
        assert stock.zone.name in stock_str


# ============= StockCard Model Tests =============

@pytest.mark.django_db
class TestStockCardModel:
    """Test StockCard for tracking stock movements"""
    
    def test_stockcard_creation(self, db, product, zone):
        """Test creating a stock card entry"""
        card = StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='supply',
            reference='SUP-001',
            quantity_in=Decimal('50.00'),
            quantity_out=Decimal('0.00'),
            notes='Initial supply'
        )
        assert card.id is not None
        assert card.transaction_type == 'supply'
        assert card.quantity_in == Decimal('50.00')
    
    def test_stockcard_sale_transaction(self, db, product, zone):
        """Test stock card for sale transaction"""
        card = StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='sale',
            reference='VNT-2025-001',
            quantity_in=Decimal('0.00'),
            quantity_out=Decimal('10.00')
        )
        assert card.quantity_out == Decimal('10.00')
        assert card.quantity_in == Decimal('0.00')
    
    def test_stockcard_transfer_in(self, db, product, zone):
        """Test stock card for transfer in"""
        card = StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='transfer_in',
            reference='TRF-001',
            quantity_in=Decimal('25.00'),
            quantity_out=Decimal('0.00')
        )
        assert card.transaction_type == 'transfer_in'
        assert card.quantity_in == Decimal('25.00')
    
    def test_stockcard_ordering(self, db, product, zone):
        """Test stock card ordering by date"""
        card1 = StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='supply',
            reference='SUP-001',
            quantity_in=Decimal('10.00'),
            quantity_out=Decimal('0.00')
        )
        card2 = StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='sale',
            reference='VNT-001',
            quantity_in=Decimal('0.00'),
            quantity_out=Decimal('5.00')
        )
        
        cards = StockCard.objects.filter(product=product, zone=zone).order_by('-date')
        assert cards.count() == 2


# ============= StockTransfer Model Tests =============

@pytest.mark.django_db
class TestStockTransferModel:
    """Test stock transfer between zones"""
    
    def test_stock_transfer_creation(self, db, zone):
        """Test creating a stock transfer"""
        zone2 = zone
        from apps.core.models import Zone
        zone1 = Zone.objects.create(name="Zone A", address="Address A")
        
        transfer = StockTransfer.objects.create(
            from_zone=zone1,
            to_zone=zone2,
            date=date.today(),
            status='pending',
            notes='Test transfer'
        )
        assert transfer.id is not None
        assert transfer.from_zone == zone1
        assert transfer.to_zone == zone2
    
    def test_stock_transfer_with_items(self, db, product, zone):
        """Test stock transfer with items"""
        from apps.core.models import Zone
        zone1 = Zone.objects.create(name="Zone A")
        zone2 = Zone.objects.create(name="Zone B")
        
        transfer = StockTransfer.objects.create(
            from_zone=zone1,
            to_zone=zone2,
            date=date.today(),
            status='pending'
        )
        
        item = StockTransferItem.objects.create(
            transfer=transfer,
            product=product,
            quantity=Decimal('20.00'),
            transferred_quantity=Decimal('0.00')
        )
        
        assert transfer.items.count() == 1
        assert item.quantity == Decimal('20.00')


# ============= Product API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestProductAPI:
    """Test Product API endpoints"""
    
    def test_list_products(self, authenticated_client, product):
        """Test listing products"""
        url = reverse('product-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_product(self, admin_client, product_category, unit_of_measure):
        """Test creating a product via API"""
        url = reverse('product-list')
        data = {
            'name': 'New Product',
            'category': product_category.id,
            'unit': unit_of_measure.id,
            'purchase_price': '80.00',
            'selling_price': '120.00',
            'is_raw_material': False,
            'is_active': True,
            'min_stock_level': '5.00'
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Product'
        
        # Verify in database
        product = Product.objects.get(name='New Product')
        assert product.selling_price == Decimal('120.00')
    
    def test_retrieve_product(self, authenticated_client, product):
        """Test retrieving a specific product"""
        url = reverse('product-detail', kwargs={'pk': product.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == product.name
    
    def test_update_product(self, admin_client, product):
        """Test updating a product"""
        url = reverse('product-detail', kwargs={'pk': product.id})
        data = {
            'name': 'Updated Product',
            'category': product.category.id,
            'unit': product.unit.id,
            'purchase_price': '110.00',
            'selling_price': '165.00',
            'is_active': True
        }
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        product.refresh_from_db()
        assert product.name == 'Updated Product'
        assert product.selling_price == Decimal('165.00')
    
    def test_deactivate_product(self, admin_client, product):
        """Test deactivating a product"""
        url = reverse('product-detail', kwargs={'pk': product.id})
        data = {'is_active': False}
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        product.refresh_from_db()
        assert product.is_active is False
    
    def test_filter_products_by_category(self, authenticated_client, product, product_category):
        """Test filtering products by category"""
        url = reverse('product-list')
        response = authenticated_client.get(url, {'category': product_category.id})
        assert response.status_code == status.HTTP_200_OK
        for product_data in response.data['results']:
            assert product_data['category'] == product_category.id
    
    def test_search_products_by_name(self, authenticated_client, product):
        """Test searching products by name"""
        url = reverse('product-list')
        response = authenticated_client.get(url, {'search': 'Test'})
        assert response.status_code == status.HTTP_200_OK


# ============= Stock API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestStockAPI:
    """Test Stock API endpoints"""
    
    def test_list_stock(self, authenticated_client, stock):
        """Test listing stock"""
        url = reverse('stock-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_retrieve_stock(self, authenticated_client, stock):
        """Test retrieving specific stock"""
        url = reverse('stock-detail', kwargs={'pk': stock.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['quantity']) == stock.quantity
    
    def test_filter_stock_by_zone(self, authenticated_client, stock, zone):
        """Test filtering stock by zone"""
        url = reverse('stock-list')
        response = authenticated_client.get(url, {'zone': zone.id})
        assert response.status_code == status.HTTP_200_OK
        for stock_data in response.data['results']:
            assert stock_data['zone'] == zone.id
    
    def test_filter_stock_by_product(self, authenticated_client, stock, product):
        """Test filtering stock by product"""
        url = reverse('stock-list')
        response = authenticated_client.get(url, {'product': product.id})
        assert response.status_code == status.HTTP_200_OK
        for stock_data in response.data['results']:
            assert stock_data['product'] == product.id
    
    def test_low_stock_alert(self, authenticated_client, db, product, zone):
        """Test low stock filtering"""
        # Create stock below minimum level
        low_stock = Stock.objects.create(
            product=product,
            zone=zone,
            quantity=Decimal('5.00')
        )
        product.min_stock_level = Decimal('10.00')
        product.save()
        
        url = reverse('stock-list')
        response = authenticated_client.get(url, {'low_stock': 'true'})
        assert response.status_code == status.HTTP_200_OK


# ============= Integration Tests =============

@pytest.mark.django_db
@pytest.mark.integration
class TestStockMovementIntegration:
    """Integration tests for stock movements"""
    
    def test_complete_stock_flow(self, db, product, zone):
        """Test complete stock flow: supply -> sale -> return"""
        # Initial stock
        stock = Stock.objects.create(
            product=product,
            zone=zone,
            quantity=Decimal('0.00')
        )
        
        # Supply
        supply_qty = Decimal('100.00')
        stock.quantity += supply_qty
        stock.save()
        StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='supply',
            reference='SUP-001',
            quantity_in=supply_qty,
            quantity_out=Decimal('0.00')
        )
        assert stock.quantity == Decimal('100.00')
        
        # Sale
        sale_qty = Decimal('30.00')
        stock.quantity -= sale_qty
        stock.save()
        StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='sale',
            reference='VNT-001',
            quantity_in=Decimal('0.00'),
            quantity_out=sale_qty
        )
        assert stock.quantity == Decimal('70.00')
        
        # Return
        return_qty = Decimal('5.00')
        stock.quantity += return_qty
        stock.save()
        StockCard.objects.create(
            product=product,
            zone=zone,
            date=date.today(),
            transaction_type='return',
            reference='RET-001',
            quantity_in=return_qty,
            quantity_out=Decimal('0.00')
        )
        assert stock.quantity == Decimal('75.00')
        
        # Verify stock cards
        cards = StockCard.objects.filter(product=product, zone=zone)
        assert cards.count() == 3
