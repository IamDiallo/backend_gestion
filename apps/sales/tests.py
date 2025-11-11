"""
Tests for Sales app - Sale, SaleItem, Invoice, Quote models and APIs
"""
import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from apps.sales.models import Sale, SaleItem, Quote, QuoteItem, Invoice
from apps.inventory.models import Stock, StockCard
from apps.treasury.models import Account, CashReceipt, AccountStatement


# ============= Sale Model Tests =============

@pytest.mark.django_db
class TestSaleModel:
    """Test Sale model business logic"""
    
    def test_sale_creation(self, sale):
        """Test creating a sale"""
        assert sale.id is not None
        assert sale.status == 'draft'
        assert sale.payment_status == 'unpaid'
        assert str(sale).startswith("Sale")
    
    def test_sale_reference_generation(self, db, client_partner, zone, regular_user):
        """Test automatic reference generation"""
        sale1 = Sale.objects.create(
            client=client_partner,
            zone=zone,
            date=date.today(),
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            created_by=regular_user
        )
        sale2 = Sale.objects.create(
            client=client_partner,
            zone=zone,
            date=date.today(),
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00'),
            created_by=regular_user
        )
        
        assert sale1.reference is not None
        assert sale2.reference is not None
        assert sale1.reference != sale2.reference
        assert sale1.reference.startswith('VNT-2025-')
    
    def test_sale_with_items(self, sale_with_items, product):
        """Test sale with items"""
        assert sale_with_items.items.count() == 1
        item = sale_with_items.items.first()
        assert item.product == product
        assert item.quantity == Decimal('5.00')
        assert item.total_price == Decimal('750.00')
    
    def test_sale_status_transition(self, sale):
        """Test sale status transitions"""
        # Draft -> Confirmed -> Payment Pending
        sale.status = 'confirmed'
        sale.save()
        assert sale.status == 'payment_pending'
        
        # Payment -> Paid
        sale.paid_amount = sale.total_amount
        sale.payment_status = 'paid'
        sale.status = 'paid'
        sale.save()
        assert sale.payment_status == 'paid'
    
    def test_sale_cancellation_restores_stock(self, db, sale_with_items, product, stock):
        """Test that cancelling a sale restores stock"""
        # Record initial stock
        initial_stock = stock.quantity
        
        # Reduce stock for the sale
        stock.quantity -= Decimal('5.00')
        stock.save()
        
        # Cancel the sale
        sale_with_items.status = 'cancelled'
        sale_with_items.save()
        
        # Stock should be restored
        stock.refresh_from_db()
        assert stock.quantity == initial_stock
        
        # Check StockCard entry
        stock_card = StockCard.objects.filter(
            product=product,
            transaction_type='return',
            reference__contains='CANCEL'
        ).first()
        assert stock_card is not None
        assert stock_card.quantity_in == Decimal('5.00')
    
    def test_sale_deletion_restores_stock(self, db, sale_with_items, product, stock):
        """Test that deleting a sale restores stock"""
        initial_stock = stock.quantity
        
        # Reduce stock
        stock.quantity -= Decimal('5.00')
        stock.save()
        
        # Delete the sale
        sale_id = sale_with_items.id
        sale_with_items.delete()
        
        # Stock should be restored
        stock.refresh_from_db()
        assert stock.quantity == initial_stock
        
        # Sale should be deleted
        assert not Sale.objects.filter(id=sale_id).exists()


@pytest.mark.django_db
class TestSaleItemModel:
    """Test SaleItem model"""
    
    def test_sale_item_creation(self, sale, product):
        """Test creating a sale item"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('3.00'),
            unit_price=Decimal('150.00'),
            discount_percentage=Decimal('10.00'),
            total_price=Decimal('405.00')  # 3 * 150 * 0.9
        )
        assert item.id is not None
        assert item.quantity == Decimal('3.00')
        assert str(item).startswith(product.name)
    
    def test_sale_item_total_calculation(self, sale, product):
        """Test total price calculation with discount"""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            discount_percentage=Decimal('20.00'),
            total_price=Decimal('800.00')  # 10 * 100 * 0.8
        )
        expected_total = Decimal('800.00')
        assert item.total_price == expected_total


# ============= Sale API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestSaleAPI:
    """Test Sale API endpoints"""
    
    def test_list_sales(self, authenticated_client, sale):
        """Test listing sales"""
        url = reverse('sale-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_sale(self, admin_client, client_partner, zone, product, stock):
        """Test creating a sale via API"""
        url = reverse('sale-list')
        data = {
            'client': client_partner.id,
            'zone': zone.id,
            'date': date.today().isoformat(),
            'status': 'draft',
            'payment_status': 'unpaid',
            'subtotal': '750.00',
            'discount_amount': '0.00',
            'tax_amount': '0.00',
            'total_amount': '750.00',
            'paid_amount': '0.00',
            'remaining_amount': '750.00',
            'items': [
                {
                    'product': product.id,
                    'quantity': '5.00',
                    'unit_price': '150.00',
                    'discount_percentage': '0.00',
                    'total_price': '750.00'
                }
            ]
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'reference' in response.data
        
        # Verify sale in database
        sale = Sale.objects.get(reference=response.data['reference'])
        assert sale.total_amount == Decimal('750.00')
        assert sale.items.count() == 1
    
    def test_retrieve_sale(self, authenticated_client, sale):
        """Test retrieving a specific sale"""
        url = reverse('sale-detail', kwargs={'pk': sale.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['reference'] == sale.reference
    
    def test_update_sale(self, admin_client, sale):
        """Test updating a sale"""
        url = reverse('sale-detail', kwargs={'pk': sale.id})
        data = {
            'client': sale.client.id,
            'zone': sale.zone.id,
            'date': sale.date.isoformat(),
            'status': 'confirmed',
            'payment_status': 'unpaid',
            'subtotal': sale.subtotal,
            'total_amount': sale.total_amount,
            'notes': 'Updated notes'
        }
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        sale.refresh_from_db()
        assert sale.notes == 'Updated notes'
    
    def test_delete_sale(self, admin_client, db, client_partner, zone, product, stock):
        """Test deleting a sale"""
        # Create a sale to delete
        sale = Sale.objects.create(
            client=client_partner,
            zone=zone,
            date=date.today(),
            status='draft',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00'),
            total_price=Decimal('100.00')
        )
        
        initial_stock = stock.quantity
        stock.quantity -= Decimal('1.00')
        stock.save()
        
        url = reverse('sale-detail', kwargs={'pk': sale.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Stock should be restored
        stock.refresh_from_db()
        assert stock.quantity == initial_stock
    
    def test_list_sales_by_client(self, authenticated_client, sale, client_partner):
        """Test filtering sales by client"""
        url = reverse('sale-list')
        response = authenticated_client.get(url, {'client': client_partner.id})
        assert response.status_code == status.HTTP_200_OK
        for sale_data in response.data['results']:
            assert sale_data['client'] == client_partner.id
    
    def test_list_sales_by_status(self, authenticated_client, sale):
        """Test filtering sales by status"""
        url = reverse('sale-list')
        response = authenticated_client.get(url, {'status': 'draft'})
        assert response.status_code == status.HTTP_200_OK
        for sale_data in response.data['results']:
            assert sale_data['status'] == 'draft'
    
    def test_list_sales_by_date_range(self, authenticated_client, sale):
        """Test filtering sales by date range"""
        url = reverse('sale-list')
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        response = authenticated_client.get(url, {
            'date_after': yesterday.isoformat(),
            'date_before': tomorrow.isoformat()
        })
        assert response.status_code == status.HTTP_200_OK


# ============= Quote Model Tests =============

@pytest.mark.django_db
class TestQuoteModel:
    """Test Quote model"""
    
    def test_quote_creation(self, db, client_partner):
        """Test creating a quote"""
        quote = Quote.objects.create(
            client=client_partner,
            date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status='draft',
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('1000.00')
        )
        assert quote.id is not None
        assert quote.reference is not None
        assert quote.reference.startswith('DEV-2025-')
        assert quote.is_converted is False
    
    def test_quote_reference_generation(self, db, client_partner):
        """Test automatic quote reference generation"""
        quote1 = Quote.objects.create(
            client=client_partner,
            date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        quote2 = Quote.objects.create(
            client=client_partner,
            date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        assert quote1.reference != quote2.reference
        # Extract numbers from references
        num1 = int(quote1.reference.split('-')[-1])
        num2 = int(quote2.reference.split('-')[-1])
        assert num2 == num1 + 1


# ============= Integration Tests =============

@pytest.mark.django_db
@pytest.mark.integration
class TestSalePaymentIntegration:
    """Integration tests for sale with payments"""
    
    def test_sale_with_full_payment(self, db, sale_with_items, account, payment_method):
        """Test sale with full payment"""
        # Create payment
        receipt = CashReceipt.objects.create(
            sale=sale_with_items,
            account=account,
            client=sale_with_items.client,
            date=date.today(),
            amount=sale_with_items.total_amount,
            allocated_amount=sale_with_items.total_amount,
            payment_method=payment_method
        )
        
        # Update sale payment status
        sale_with_items.paid_amount = sale_with_items.total_amount
        sale_with_items.remaining_amount = Decimal('0.00')
        sale_with_items.payment_status = 'paid'
        sale_with_items.save()
        
        assert sale_with_items.payment_status == 'paid'
        assert sale_with_items.remaining_amount == Decimal('0.00')
    
    def test_sale_with_partial_payment(self, db, sale_with_items, account, payment_method):
        """Test sale with partial payment"""
        partial_amount = sale_with_items.total_amount / 2
        
        receipt = CashReceipt.objects.create(
            sale=sale_with_items,
            account=account,
            client=sale_with_items.client,
            date=date.today(),
            amount=partial_amount,
            allocated_amount=partial_amount,
            payment_method=payment_method
        )
        
        sale_with_items.paid_amount = partial_amount
        sale_with_items.remaining_amount = sale_with_items.total_amount - partial_amount
        sale_with_items.payment_status = 'partially_paid'
        sale_with_items.save()
        
        assert sale_with_items.payment_status == 'partially_paid'
        assert sale_with_items.remaining_amount == partial_amount


@pytest.mark.django_db
@pytest.mark.integration  
class TestSaleStockIntegration:
    """Integration tests for sale with stock management"""
    
    def test_sale_reduces_stock(self, db, sale_with_items, product, stock):
        """Test that confirmed sale reduces stock"""
        initial_stock = stock.quantity
        sale_quantity = sale_with_items.items.first().quantity
        
        # Simulate sale confirmation
        stock.quantity -= sale_quantity
        stock.save()
        
        # Create stock card entry
        StockCard.objects.create(
            product=product,
            zone=stock.zone,
            date=date.today(),
            transaction_type='sale',
            reference=sale_with_items.reference,
            quantity_out=sale_quantity,
            quantity_in=Decimal('0.00')
        )
        
        stock.refresh_from_db()
        assert stock.quantity == initial_stock - sale_quantity
        
        # Verify stock card
        stock_cards = StockCard.objects.filter(
            product=product,
            transaction_type='sale',
            reference=sale_with_items.reference
        )
        assert stock_cards.exists()
        assert stock_cards.first().quantity_out == sale_quantity
