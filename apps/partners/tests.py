"""
Tests for Partners app - Client, Supplier models and APIs
"""
import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal

from apps.partners.models import Client, Supplier


# ============= Client Model Tests =============

@pytest.mark.django_db
class TestClientModel:
    """Test Client model"""
    
    def test_client_creation(self, client_partner):
        """Test creating a client"""
        assert client_partner.id is not None
        assert client_partner.name == "Test Client"
        assert client_partner.phone == "622123456"
        assert client_partner.is_active is True
    
    def test_client_str_representation(self, client_partner):
        """Test string representation"""
        assert str(client_partner) == "Test Client"
    
    def test_client_with_email(self, db):
        """Test client with email"""
        from conftest import ClientFactory
        client = ClientFactory(
            name="Email Client",
            email="email@client.com",
            phone="622999888"
        )
        assert client.email == "email@client.com"
    
    def test_client_deactivation(self, client_partner):
        """Test deactivating a client"""
        client_partner.is_active = False
        client_partner.save()
        client_partner.refresh_from_db()
        assert client_partner.is_active is False
    
    def test_client_update_info(self, client_partner):
        """Test updating client information"""
        client_partner.address = "New Address 123"
        client_partner.phone = "622555444"
        client_partner.save()
        
        client_partner.refresh_from_db()
        assert client_partner.address == "New Address 123"
        assert client_partner.phone == "622555444"


# ============= Supplier Model Tests =============

@pytest.mark.django_db
class TestSupplierModel:
    """Test Supplier model"""
    
    def test_supplier_creation(self, supplier_partner):
        """Test creating a supplier"""
        assert supplier_partner.id is not None
        assert supplier_partner.name == "Test Supplier"
        assert supplier_partner.phone == "622654321"
        assert supplier_partner.is_active is True
    
    def test_supplier_str_representation(self, supplier_partner):
        """Test string representation"""
        assert str(supplier_partner) == "Test Supplier"
    
    def test_supplier_with_contact_person(self, db):
        """Test supplier with contact person"""
        from conftest import SupplierFactory
        supplier = SupplierFactory(
            name="Supplier with Contact",
            phone="622111222"
        )
        assert supplier.name == "Supplier with Contact"
    
    def test_supplier_deactivation(self, supplier_partner):
        """Test deactivating a supplier"""
        supplier_partner.is_active = False
        supplier_partner.save()
        supplier_partner.refresh_from_db()
        assert supplier_partner.is_active is False


# ============= Client API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestClientAPI:
    """Test Client API endpoints"""
    
    def test_list_clients(self, authenticated_client, client_partner):
        """Test listing clients"""
        url = reverse('client-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_client(self, admin_client, account):
        """Test creating a client via API"""
        url = reverse('client-list')
        data = {
            'name': 'New Client',
            'contact_person': 'John Doe',
            'phone': '622777888',
            'email': 'newclient@example.com',
            'address': '123 Client Street',
            'account': account.id,
            'is_active': True
        }
        response = admin_client.post(url, data, format='json')
        # Debug: print response if test fails
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Client'
        
        # Verify in database
        client = Client.objects.get(name='New Client')
        assert client.phone == '622777888'
    
    def test_retrieve_client(self, authenticated_client, client_partner):
        """Test retrieving a specific client"""
        url = reverse('client-detail', kwargs={'pk': client_partner.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == client_partner.name
        assert response.data['phone'] == client_partner.phone
    
    def test_update_client(self, admin_client, client_partner):
        """Test updating a client"""
        url = reverse('client-detail', kwargs={'pk': client_partner.id})
        data = {
            'name': 'Updated Client Name',
            'phone': '622999000',
            'email': 'updated@client.com',
            'address': client_partner.address,
            'is_active': True
        }
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        client_partner.refresh_from_db()
        assert client_partner.name == 'Updated Client Name'
        assert client_partner.phone == '622999000'
    
    def test_delete_client(self, admin_client, db):
        """Test deleting a client"""
        from conftest import ClientFactory
        client_to_delete = ClientFactory(
            name="Client to Delete",
            phone="622888999"
        )
        
        url = reverse('client-detail', kwargs={'pk': client_to_delete.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        assert not Client.objects.filter(id=client_to_delete.id).exists()
    
    def test_search_clients_by_name(self, authenticated_client, client_partner):
        """Test searching clients by name"""
        url = reverse('client-list')
        response = authenticated_client.get(url, {'search': 'Test'})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_filter_active_clients(self, authenticated_client, db):
        """Test filtering active clients"""
        from conftest import ClientFactory
        active_client = ClientFactory(name="Active Client", is_active=True)
        inactive_client = ClientFactory(name="Inactive Client", is_active=False)
        
        url = reverse('client-list')
        response = authenticated_client.get(url, {'is_active': 'true'})
        assert response.status_code == status.HTTP_200_OK
        
        names = [item['name'] for item in response.data['results']]
        assert 'Active Client' in names


# ============= Supplier API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestSupplierAPI:
    """Test Supplier API endpoints"""
    
    def test_list_suppliers(self, authenticated_client, supplier_partner):
        """Test listing suppliers"""
        url = reverse('supplier-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_supplier(self, admin_client, account):
        """Test creating a supplier via API"""
        url = reverse('supplier-list')
        data = {
            'name': 'New Supplier',
            'contact_person': 'Jane Smith',
            'phone': '622333444',
            'email': 'newsupplier@example.com',
            'address': '456 Supplier Avenue',
            'account': account.id,
            'is_active': True
        }
        response = admin_client.post(url, data, format='json')
        # Debug: print response if test fails
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Supplier'
        
        # Verify in database
        supplier = Supplier.objects.get(name='New Supplier')
        assert supplier.phone == '622333444'
    
    def test_retrieve_supplier(self, authenticated_client, supplier_partner):
        """Test retrieving a specific supplier"""
        url = reverse('supplier-detail', kwargs={'pk': supplier_partner.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == supplier_partner.name
    
    def test_update_supplier(self, admin_client, supplier_partner):
        """Test updating a supplier"""
        url = reverse('supplier-detail', kwargs={'pk': supplier_partner.id})
        data = {
            'name': 'Updated Supplier Name',
            'phone': '622444555',
            'email': 'updated@supplier.com',
            'address': supplier_partner.address,
            'is_active': True
        }
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        supplier_partner.refresh_from_db()
        assert supplier_partner.name == 'Updated Supplier Name'
        assert supplier_partner.phone == '622444555'
    
    def test_delete_supplier(self, admin_client, db):
        """Test deleting a supplier"""
        from conftest import SupplierFactory
        supplier_to_delete = SupplierFactory(
            name="Supplier to Delete",
            phone="622666777"
        )
        
        url = reverse('supplier-detail', kwargs={'pk': supplier_to_delete.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        assert not Supplier.objects.filter(id=supplier_to_delete.id).exists()
    
    def test_search_suppliers_by_name(self, authenticated_client, supplier_partner):
        """Test searching suppliers by name"""
        url = reverse('supplier-list')
        response = authenticated_client.get(url, {'search': 'Test'})
        assert response.status_code == status.HTTP_200_OK
    
    def test_filter_active_suppliers(self, authenticated_client, db):
        """Test filtering active suppliers"""
        from conftest import SupplierFactory
        active_supplier = SupplierFactory(name="Active Supplier", is_active=True)
        inactive_supplier = SupplierFactory(name="Inactive Supplier", is_active=False)
        
        url = reverse('supplier-list')
        response = authenticated_client.get(url, {'is_active': 'true'})
        assert response.status_code == status.HTTP_200_OK


# ============= Integration Tests =============

@pytest.mark.django_db
@pytest.mark.integration
class TestPartnerIntegration:
    """Integration tests for partners with sales and supplies"""
    
    def test_client_with_sales(self, db, client_partner, zone, product, regular_user):
        """Test client with associated sales"""
        from apps.sales.models import Sale, SaleItem
        
        # Create sales for the client
        sale1 = Sale.objects.create(
            client=client_partner,
            zone=zone,
            date='2025-01-15',
            status='confirmed',
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            created_by=regular_user
        )
        sale2 = Sale.objects.create(
            client=client_partner,
            zone=zone,
            date='2025-01-20',
            status='paid',
            subtotal=Decimal('1500.00'),
            total_amount=Decimal('1500.00'),
            created_by=regular_user
        )
        
        # Verify client has sales
        assert client_partner.sales.count() == 2
        total_sales = sum(sale.total_amount for sale in client_partner.sales.all())
        assert total_sales == Decimal('2500.00')
    
    def test_supplier_with_supplies(self, db, supplier_partner, zone, product):
        """Test supplier with associated supplies"""
        from apps.inventory.models import StockSupply, StockSupplyItem
        
        # Create supply from the supplier
        supply = StockSupply.objects.create(
            supplier=supplier_partner,
            zone=zone,
            date='2025-01-10',
            status='received',
            total_amount=Decimal('5000.00')
        )
        StockSupplyItem.objects.create(
            supply=supply,
            product=product,
            quantity=Decimal('50.00'),
            unit_price=Decimal('100.00'),
            total_price=Decimal('5000.00')
        )
        
        # Verify supplier has supplies
        assert supplier_partner.inventory_stock_supplies.count() == 1
        supply_total = supplier_partner.inventory_stock_supplies.first().total_amount
        assert supply_total == Decimal('5000.00')
    
    def test_client_account_balance(self, db, client_partner, currency):
        """Test client with account balance tracking"""
        from apps.treasury.models import Account, AccountStatement
        
        # Create client account
        client_account = Account.objects.create(
            name=f"Client - {client_partner.name}",
            account_type='client',
            currency=currency,
            current_balance=Decimal('-5000.00')  # Client owes money
        )
        
        # Create statement entries
        AccountStatement.objects.create(
            account=client_account,
            date='2025-01-15',
            transaction_type='sale',
            reference='VNT-2025-001',
            description='Sale to client',
            debit=Decimal('5000.00'),
            credit=Decimal('0.00'),
            balance=Decimal('-5000.00')
        )
        
        statements = AccountStatement.objects.filter(account=client_account)
        assert statements.count() == 1
        assert client_account.current_balance == Decimal('-5000.00')
