"""
Pytest configuration and shared fixtures for all tests
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from decimal import Decimal
from datetime import date, timedelta
import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.core.models import UserProfile, Zone
from apps.partners.models import Client, Supplier
from apps.app_settings.models import (
    Currency, ProductCategory, UnitOfMeasure, 
    PaymentMethod, ExpenseCategory
)
from apps.inventory.models import Product, Stock
from apps.sales.models import Sale, SaleItem
from apps.treasury.models import Account

fake = Faker()


# ============= Factories =============

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)
        else:
            self.set_password('testpass123')


class ZoneFactory(DjangoModelFactory):
    class Meta:
        model = Zone
    
    name = factory.Sequence(lambda n: f"Zone {n}")
    address = factory.Faker('street_address')  # Shorter address
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile
    
    user = factory.SubFactory(UserFactory)
    role = 'commercial'
    zone = factory.SubFactory(ZoneFactory)
    is_active = True


class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency
        django_get_or_create = ('code',)
    
    name = factory.Sequence(lambda n: f"Currency {n}")
    code = factory.Sequence(lambda n: chr(65 + (n % 26)) + chr(65 + ((n // 26) % 26)) + chr(65 + ((n // 676) % 26)))  # AAA, AAB, AAC, etc.
    symbol = factory.Sequence(lambda n: f"${n%10}")  # Keep symbol short too
    is_base = False
    is_active = True


class ProductCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ProductCategory
    
    name = factory.Sequence(lambda n: f"Category {n}")
    description = factory.Faker('text', max_nb_chars=100)


class UnitOfMeasureFactory(DjangoModelFactory):
    class Meta:
        model = UnitOfMeasure
        django_get_or_create = ('symbol',)
    
    name = factory.Sequence(lambda n: f"Unit {n}")
    symbol = factory.Sequence(lambda n: f"U{n}")


class PaymentMethodFactory(DjangoModelFactory):
    class Meta:
        model = PaymentMethod
    
    name = factory.Sequence(lambda n: f"Payment Method {n}")
    description = factory.Faker('text', max_nb_chars=100)
    is_active = True


class ExpenseCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ExpenseCategory
    
    name = factory.Sequence(lambda n: f"Expense Category {n}")
    description = factory.Faker('text', max_nb_chars=100)


class AccountFactory(DjangoModelFactory):
    class Meta:
        model = Account
    
    name = factory.Sequence(lambda n: f"Account {n}")
    account_type = 'cash'
    currency = factory.SubFactory(CurrencyFactory)
    initial_balance = Decimal('10000.00')
    current_balance = Decimal('10000.00')
    is_active = True


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client
    
    name = factory.Faker('company')
    contact_person = factory.Faker('name')
    phone = factory.Sequence(lambda n: f"622{n:06d}")
    email = factory.Faker('email')
    address = factory.Faker('street_address')  # Shorter than full address
    account = factory.SubFactory(AccountFactory)
    is_active = True


class SupplierFactory(DjangoModelFactory):
    class Meta:
        model = Supplier
    
    name = factory.Faker('company')
    contact_person = factory.Faker('name')
    phone = factory.Sequence(lambda n: f"622{n:06d}")
    email = factory.Faker('email')
    address = factory.Faker('street_address')  # Shorter than full address
    account = factory.SubFactory(AccountFactory)
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
    
    name = factory.Sequence(lambda n: f"Product {n}")
    reference = factory.Sequence(lambda n: f"PROD-{n:04d}")
    category = factory.SubFactory(ProductCategoryFactory)
    unit = factory.SubFactory(UnitOfMeasureFactory)
    purchase_price = Decimal('100.00')
    selling_price = Decimal('150.00')
    is_raw_material = False
    is_active = True
    min_stock_level = Decimal('10.00')


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock
    
    product = factory.SubFactory(ProductFactory)
    zone = factory.SubFactory(ZoneFactory)
    quantity = Decimal('100.00')


class SaleFactory(DjangoModelFactory):
    class Meta:
        model = Sale
    
    reference = factory.Sequence(lambda n: f"VNT-2025-{n:03d}")
    client = factory.SubFactory(ClientFactory)
    zone = factory.SubFactory(ZoneFactory)
    date = factory.LazyFunction(date.today)
    created_by = factory.SubFactory(UserFactory)
    status = 'draft'
    payment_status = 'unpaid'
    workflow_state = 'draft'
    subtotal = Decimal('1000.00')
    discount_amount = Decimal('0.00')
    tax_amount = Decimal('0.00')
    total_amount = Decimal('1000.00')
    paid_amount = Decimal('0.00')
    remaining_amount = Decimal('1000.00')


class SaleItemFactory(DjangoModelFactory):
    class Meta:
        model = SaleItem
    
    sale = factory.SubFactory(SaleFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = Decimal('10.00')
    unit_price = Decimal('100.00')
    discount_percentage = Decimal('0.00')
    total_price = Decimal('1000.00')


# ============= Fixtures =============

@pytest.fixture
def api_client():
    """DRF API client for testing endpoints"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    user = UserFactory(
        username='admin',
        email='admin@example.com',
        is_staff=True,
        is_superuser=True
    )
    user.set_password('admin123')
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user"""
    user = UserFactory(username='testuser', email='test@example.com')
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def zone(db):
    """Create a test zone"""
    return ZoneFactory(name="Test Zone", address="123 Test St")


@pytest.fixture
def user_profile(db, regular_user, zone):
    """Create a user profile"""
    # Check if profile already exists for this user (created by signal)
    profile, created = UserProfile.objects.get_or_create(
        user=regular_user,
        defaults={
            'role': 'commercial',
            'zone': zone
        }
    )
    # Update the profile if it already existed with different values
    if not created:
        profile.role = 'commercial'
        profile.zone = zone
        profile.save()
    return profile


@pytest.fixture
def currency(db):
    """Create a test currency"""
    return CurrencyFactory(name="Franc Guinéen", code="GNF", symbol="FG")


@pytest.fixture
def unit_of_measure(db):
    """Create a unit of measure"""
    return UnitOfMeasureFactory(name="Kilogram", symbol="kg")


@pytest.fixture
def product_category(db):
    """Create a product category"""
    return ProductCategoryFactory(name="Electronics")


@pytest.fixture
def payment_method(db):
    """Create a payment method"""
    return PaymentMethodFactory(name="Cash")


@pytest.fixture
def client_partner(db):
    """Create a test client"""
    return ClientFactory(
        name="Test Client",
        phone="622123456",
        email="client@example.com"
    )


@pytest.fixture
def supplier_partner(db):
    """Create a test supplier"""
    return SupplierFactory(
        name="Test Supplier",
        phone="622654321",
        email="supplier@example.com"
    )


@pytest.fixture
def product(db, product_category, unit_of_measure):
    """Create a test product"""
    return ProductFactory(
        name="Test Product",
        category=product_category,
        unit=unit_of_measure,
        purchase_price=Decimal('100.00'),
        selling_price=Decimal('150.00')
    )


@pytest.fixture
def stock(db, product, zone):
    """Create stock for a product"""
    return StockFactory(
        product=product,
        zone=zone,
        quantity=Decimal('100.00')
    )


@pytest.fixture
def account(db, currency):
    """Create a test account"""
    return AccountFactory(
        name="Main Cash Account",
        account_type='cash',
        currency=currency,
        current_balance=Decimal('50000.00')
    )


@pytest.fixture
def sale(db, client_partner, zone, regular_user):
    """Create a test sale"""
    return SaleFactory(
        client=client_partner,
        zone=zone,
        created_by=regular_user,
        date=date.today()
    )


@pytest.fixture
def sale_with_items(db, sale, product, stock):
    """Create a sale with items"""
    SaleItemFactory(
        sale=sale,
        product=product,
        quantity=Decimal('5.00'),
        unit_price=Decimal('150.00'),
        total_price=Decimal('750.00')
    )
    sale.subtotal = Decimal('750.00')
    sale.total_amount = Decimal('750.00')
    sale.remaining_amount = Decimal('750.00')
    sale.save()
    return sale


@pytest.fixture
def authenticated_client(api_client, regular_user):
    """API client authenticated as regular user"""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client authenticated as admin"""
    api_client.force_authenticate(user=admin_user)
    return api_client
