import os
import django
import random
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_backend.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User, Group, Permission
from gestion_api.models import (
    UserProfile, Zone, Currency, ExchangeRate, ProductCategory, 
    Product, UnitOfMeasure, PaymentMethod, Account, PriceGroup,
    ExpenseCategory, Client, Supplier, Sale, SaleItem, Expense,
    ClientPayment, SupplierPayment, AccountTransfer
)
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

def create_permissions():
    """Create custom permission groups with specific permissions"""
    
    # Create groups
    admin_group, _ = Group.objects.get_or_create(name="Administrators")
    manager_group, _ = Group.objects.get_or_create(name="Managers")
    sales_group, _ = Group.objects.get_or_create(name="Sales")
    warehouse_group, _ = Group.objects.get_or_create(name="Warehouse")
    
    # Get content types for our models
    client_ct = ContentType.objects.get_for_model(Client)
    product_ct = ContentType.objects.get_for_model(Product)
    category_ct = ContentType.objects.get_for_model(ProductCategory)
    zone_ct = ContentType.objects.get_for_model(Zone)
    supplier_ct = ContentType.objects.get_for_model(Supplier)
    sale_ct = ContentType.objects.get_for_model(Sale)
    sale_item_ct = ContentType.objects.get_for_model(SaleItem)
    # Let's avoid using UserProfile for production_ct and invoice_ct
    production_ct = ContentType.objects.get_for_model(Sale)  # Using Sale as a placeholder
    invoice_ct = ContentType.objects.get_for_model(Sale)  # Using Sale as a placeholder
    user_ct = ContentType.objects.get_for_model(User)
    
    # Clear existing permissions from groups
    admin_group.permissions.clear()
    manager_group.permissions.clear()
    sales_group.permissions.clear()
    warehouse_group.permissions.clear()
    
    # Add specific permissions to each group
    
    # Administrators get all permissions
    permissions = Permission.objects.all()
    if permissions.exists():  # Check if there are any permissions
        admin_group.permissions.add(*permissions)
    
    # Manager permissions
    manager_permissions = Permission.objects.filter(
        content_type__in=[
            client_ct, product_ct, category_ct, zone_ct, supplier_ct,
            sale_ct, sale_item_ct, invoice_ct, production_ct
        ]
    )
    if manager_permissions.exists():
        manager_group.permissions.add(*manager_permissions)
    
    # Add specific user management permissions for managers
    user_permissions = Permission.objects.filter(
        content_type=user_ct,
        codename__in=['view_user']
    )
    if user_permissions.exists():
        manager_group.permissions.add(*user_permissions)
    
    # Sales permissions
    sales_permissions = []
    
    # View, add, change for clients, sales, invoices
    for model_ct in [client_ct, sale_ct, sale_item_ct, invoice_ct]:
        perms = Permission.objects.filter(
            content_type=model_ct,
            codename__in=[f'view_{model_ct.model}', f'add_{model_ct.model}', f'change_{model_ct.model}']
        )
        if perms.exists():
            sales_permissions.extend(perms)
    
    # View only for products, categories, zones
    for model_ct in [product_ct, category_ct, zone_ct]:
        perms = Permission.objects.filter(
            content_type=model_ct,
            codename=f'view_{model_ct.model}'
        )
        if perms.exists():
            sales_permissions.extend(perms)
    
    if sales_permissions:
        sales_group.permissions.add(*sales_permissions)
    
    # Warehouse permissions
    warehouse_permissions = []
    
    # Full CRUD for products, productions
    for model_ct in [product_ct, production_ct, category_ct]:
        perms = Permission.objects.filter(
            content_type=model_ct
        )
        if perms.exists():
            warehouse_permissions.extend(perms)
    
    # View only for suppliers, zones
    for model_ct in [supplier_ct, zone_ct]:
        perms = Permission.objects.filter(
            content_type=model_ct,
            codename=f'view_{model_ct.model}'
        )
        if perms.exists():
            warehouse_permissions.extend(perms)
    
    if warehouse_permissions:
        warehouse_group.permissions.add(*warehouse_permissions)
    
    return {
        'admin': admin_group,
        'manager': manager_group,
        'sales': sales_group,
        'warehouse': warehouse_group
    }

def create_users(groups):
    """Create demo users for each permission group"""
    
    # Admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
    admin_user.groups.add(groups['admin'])
    
    # Ensure UserProfile exists with correct role
    admin_profile, _ = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'role': 'admin',
            'is_active': True
        }
    )
    
    # Manager user
    manager_user, created = User.objects.get_or_create(
        username='manager',
        defaults={
            'email': 'manager@example.com',
            'first_name': 'Manager',
            'last_name': 'User',
        }
    )
    if created:
        manager_user.set_password('manager123')
        manager_user.save()
    manager_user.groups.add(groups['manager'])
    
    # Ensure UserProfile exists with correct role
    manager_profile, _ = UserProfile.objects.get_or_create(
        user=manager_user,
        defaults={
            'role': 'supervisor',
            'is_active': True
        }
    )
    
    # Sales user
    sales_user, created = User.objects.get_or_create(
        username='sales',
        defaults={
            'email': 'sales@example.com',
            'first_name': 'Sales',
            'last_name': 'User',
        }
    )
    if created:
        sales_user.set_password('sales123')
        sales_user.save()
    sales_user.groups.add(groups['sales'])
    
    # Ensure UserProfile exists with correct role
    sales_profile, _ = UserProfile.objects.get_or_create(
        user=sales_user,
        defaults={
            'role': 'commercial',
            'is_active': True
        }
    )
    
    # Warehouse user
    warehouse_user, created = User.objects.get_or_create(
        username='warehouse',
        defaults={
            'email': 'warehouse@example.com',
            'first_name': 'Warehouse',
            'last_name': 'Manager',
        }
    )
    if created:
        warehouse_user.set_password('warehouse123')
        warehouse_user.save()
    warehouse_user.groups.add(groups['warehouse'])
    
    # Ensure UserProfile exists with correct role
    warehouse_profile, _ = UserProfile.objects.get_or_create(
        user=warehouse_user,
        defaults={
            'role': 'consultant',
            'is_active': True
        }
    )

def create_reference_data():
    print("Creating reference data...")
    
    # Create Zones
    zones_data = [
        {'name': 'Main Warehouse', 'address': '123 Main St', 'description': 'Primary warehouse location'},
        {'name': 'Downtown Store', 'address': '456 Market St', 'description': 'Downtown retail location'},
        {'name': 'North Branch', 'address': '789 North Rd', 'description': 'Northern district branch'},
    ]
    
    for zone_data in zones_data:
        Zone.objects.get_or_create(
            name=zone_data['name'],
            defaults={
                'address': zone_data['address'],
                'description': zone_data['description'],
                'is_active': True
            }
        )
    
    # Create Currencies
    currencies_data = [
        {'name': 'US Dollar', 'code': 'USD', 'symbol': '$', 'is_base': True},
        {'name': 'Euro', 'code': 'EUR', 'symbol': '€', 'is_base': False},
        {'name': 'British Pound', 'code': 'GBP', 'symbol': '£', 'is_base': False},
    ]
    
    for curr_data in currencies_data:
        Currency.objects.get_or_create(
            code=curr_data['code'],
            defaults={
                'name': curr_data['name'],
                'symbol': curr_data['symbol'],
                'is_base': curr_data['is_base'],
                'is_active': True
            }
        )
    
    # Create Exchange Rates
    usd = Currency.objects.get(code='USD')
    eur = Currency.objects.get(code='EUR')
    gbp = Currency.objects.get(code='GBP')
    
    rates_data = [
        {'from_currency': usd, 'to_currency': eur, 'rate': Decimal('0.85')},
        {'from_currency': usd, 'to_currency': gbp, 'rate': Decimal('0.75')},
        {'from_currency': eur, 'to_currency': usd, 'rate': Decimal('1.18')},
        {'from_currency': eur, 'to_currency': gbp, 'rate': Decimal('0.88')},
        {'from_currency': gbp, 'to_currency': usd, 'rate': Decimal('1.33')},
        {'from_currency': gbp, 'to_currency': eur, 'rate': Decimal('1.14')},
    ]
    
    for rate_data in rates_data:
        ExchangeRate.objects.get_or_create(
            from_currency=rate_data['from_currency'],
            to_currency=rate_data['to_currency'],
            date=timezone.now().date(),
            defaults={
                'rate': rate_data['rate'],
                'is_active': True
            }
        )
        
    # Create UnitOfMeasure
    units_data = [
        {'name': 'Piece', 'symbol': 'pc'},
        {'name': 'Kilogram', 'symbol': 'kg'},
        {'name': 'Liter', 'symbol': 'L'},
        {'name': 'Box', 'symbol': 'box'},
        {'name': 'Pack', 'symbol': 'pk'},
    ]
    
    for unit_data in units_data:
        UnitOfMeasure.objects.get_or_create(
            name=unit_data['name'],
            defaults={'symbol': unit_data['symbol']}
        )
    
    # Create Product Categories
    categories_data = [
        {'name': 'Electronics', 'description': 'Electronic devices and accessories'},
        {'name': 'Furniture', 'description': 'Home and office furniture'},
        {'name': 'Groceries', 'description': 'Food and household items'},
        {'name': 'Clothing', 'description': 'Clothing and apparel'},
        {'name': 'Raw Materials', 'description': 'Materials for production'},
    ]
    
    for cat_data in categories_data:
        ProductCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
    
    # Create Payment Methods
    methods_data = [
        {'name': 'Cash', 'description': 'Cash payment'},
        {'name': 'Credit Card', 'description': 'Credit card payment'},
        {'name': 'Bank Transfer', 'description': 'Direct bank transfer'},
        {'name': 'Mobile Money', 'description': 'Payment via mobile money service'},
        {'name': 'Check', 'description': 'Payment by check'},
    ]
    
    for method_data in methods_data:
        PaymentMethod.objects.get_or_create(
            name=method_data['name'],
            defaults={
                'description': method_data['description'],
                'is_active': True
            }
        )
    
    # Create Expense Categories
    exp_categories = [
        {'name': 'Rent', 'description': 'Office and warehouse rent'},
        {'name': 'Utilities', 'description': 'Electricity, water, internet'},
        {'name': 'Salaries', 'description': 'Staff salaries and wages'},
        {'name': 'Marketing', 'description': 'Advertising and promotions'},
        {'name': 'Transportation', 'description': 'Delivery and transport costs'},
    ]
    
    for exp_cat in exp_categories:
        ExpenseCategory.objects.get_or_create(
            name=exp_cat['name'],
            defaults={
                'description': exp_cat['description'],
                'is_active': True
            }
        )
    
    # Create Price Groups
    price_groups = [
        {'name': 'Regular', 'discount_percentage': Decimal('0.00'), 'description': 'Standard pricing'},
        {'name': 'Wholesale', 'discount_percentage': Decimal('5.00'), 'description': 'Wholesale customers'},
        {'name': 'VIP', 'discount_percentage': Decimal('10.00'), 'description': 'VIP customers'},
    ]
    
    for pg in price_groups:
        PriceGroup.objects.get_or_create(
            name=pg['name'],
            defaults={
                'discount_percentage': pg['discount_percentage'],
                'description': pg['description']
            }
        )

def create_accounts():
    print("Creating accounts...")
    
    # Get base currency
    usd = Currency.objects.get(code='USD')
    
    # Create Accounts
    accounts_data = [
        {'name': 'Main Cash Account', 'account_type': 'cash', 'initial_balance': Decimal('10000.00')},
        {'name': 'Business Bank Account', 'account_type': 'bank', 'initial_balance': Decimal('25000.00')},
        {'name': 'Petty Cash', 'account_type': 'cash', 'initial_balance': Decimal('1000.00')},
        {'name': 'Client Receivables', 'account_type': 'client', 'initial_balance': Decimal('0.00')},
        {'name': 'Supplier Payables', 'account_type': 'supplier', 'initial_balance': Decimal('0.00')},
    ]
    
    for acc_data in accounts_data:
        Account.objects.get_or_create(
            name=acc_data['name'],
            defaults={
                'account_type': acc_data['account_type'],
                'currency': usd,
                'initial_balance': acc_data['initial_balance'],
                'current_balance': acc_data['initial_balance'],
                'description': f"{acc_data['name']} - {acc_data['account_type']}",
                'is_active': True
            }
        )

def create_products():
    print("Creating products...")
    
    # Get categories
    electronics = ProductCategory.objects.get(name='Electronics')
    furniture = ProductCategory.objects.get(name='Furniture')
    groceries = ProductCategory.objects.get(name='Groceries')
    clothing = ProductCategory.objects.get(name='Clothing')
    raw_materials = ProductCategory.objects.get(name='Raw Materials')
    
    # Get units - get the actual objects instead of IDs
    piece = UnitOfMeasure.objects.get(name='Piece')
    kg = UnitOfMeasure.objects.get(name='Kilogram')
    liter = UnitOfMeasure.objects.get(name='Liter')
    box = UnitOfMeasure.objects.get(name='Box')
    pack = UnitOfMeasure.objects.get(name='Pack')
    
    # Create Products
    products_data = [
        {
            'name': 'Laptop', 
            'reference': 'EL001', 
            'category': electronics,
            'unit': piece,
            'purchase_price': Decimal('800.00'),
            'selling_price': Decimal('1200.00'),
            'description': 'High-performance laptop',
            'is_raw_material': False
        },
        {
            'name': 'Smartphone', 
            'reference': 'EL002', 
            'category': electronics,
            'unit': piece,
            'purchase_price': Decimal('300.00'),
            'selling_price': Decimal('500.00'),
            'description': 'Latest model smartphone',
            'is_raw_material': False
        },
        {
            'name': 'Office Chair', 
            'reference': 'FN001', 
            'category': furniture,
            'unit': piece,
            'purchase_price': Decimal('80.00'),
            'selling_price': Decimal('150.00'),
            'description': 'Ergonomic office chair',
            'is_raw_material': False
        },
        {
            'name': 'Desk', 
            'reference': 'FN002', 
            'category': furniture,
            'unit': piece,
            'purchase_price': Decimal('200.00'),
            'selling_price': Decimal('350.00'),
            'description': 'Office desk with drawers',
            'is_raw_material': False
        },
        {
            'name': 'Rice', 
            'reference': 'GR001', 
            'category': groceries,
            'unit': kg,
            'purchase_price': Decimal('0.80'),
            'selling_price': Decimal('1.50'),
            'description': 'Premium rice',
            'is_raw_material': True
        },
        {
            'name': 'Cooking Oil', 
            'reference': 'GR002', 
            'category': groceries,
            'unit': liter,
            'purchase_price': Decimal('3.00'),
            'selling_price': Decimal('5.00'),
            'description': 'Vegetable cooking oil',
            'is_raw_material': True
        },
        {
            'name': 'T-Shirt', 
            'reference': 'CL001', 
            'category': clothing,
            'unit': piece,
            'purchase_price': Decimal('5.00'),
            'selling_price': Decimal('15.00'),
            'description': 'Cotton t-shirt',
            'is_raw_material': False
        },
        {
            'name': 'Jeans', 
            'reference': 'CL002', 
            'category': clothing,
            'unit': piece,
            'purchase_price': Decimal('15.00'),
            'selling_price': Decimal('35.00'),
            'description': 'Denim jeans',
            'is_raw_material': False
        },
        {
            'name': 'Fabric', 
            'reference': 'RM001', 
            'category': raw_materials,
            'unit': kg,
            'purchase_price': Decimal('8.00'),
            'selling_price': Decimal('12.00'),
            'description': 'Raw fabric material',
            'is_raw_material': True
        },
        {
            'name': 'Wood', 
            'reference': 'RM002', 
            'category': raw_materials,
            'unit': kg,
            'purchase_price': Decimal('2.00'),
            'selling_price': Decimal('4.00'),
            'description': 'Processed wood material',
            'is_raw_material': True
        },
    ]
    
    for prod_data in products_data:
        Product.objects.get_or_create(
            reference=prod_data['reference'],
            defaults={
                'name': prod_data['name'],
                'category': prod_data['category'],
                'unit': prod_data['unit'],
                'purchase_price': prod_data['purchase_price'],
                'selling_price': prod_data['selling_price'],
                'description': prod_data['description'],
                'is_raw_material': prod_data['is_raw_material'],
                'is_active': True
            }
        )

def create_clients_suppliers():
    print("Creating clients and suppliers...")
    
    # Get price groups
    regular = PriceGroup.objects.get(name='Regular')
    wholesale = PriceGroup.objects.get(name='Wholesale')
    vip = PriceGroup.objects.get(name='VIP')
    
    # Get base currency
    usd = Currency.objects.get(code='USD')
    
    # Create Clients
    clients_data = [
        {
            'name': 'ABC Corporation',
            'contact_person': 'John Smith',
            'phone': '123-456-7890',
            'email': 'john@abccorp.com',
            'address': '123 Business Ave, Business City',
            'price_group': regular
        },
        {
            'name': 'XYZ Industries',
            'contact_person': 'Jane Doe',
            'phone': '987-654-3210',
            'email': 'jane@xyzind.com',
            'address': '456 Industry Blvd, Industry Town',
            'price_group': wholesale
        },
        {
            'name': 'LMN Enterprises',
            'contact_person': 'Robert Johnson',
            'phone': '555-123-4567',
            'email': 'robert@lmnent.com',
            'address': '789 Enterprise St, Enterprise City',
            'price_group': vip
        },
        {
            'name': 'ACME Ltd',
            'contact_person': 'Susan Williams',
            'phone': '555-987-6543',
            'email': 'susan@acmeltd.com',
            'address': '321 Corporate Dr, Business Park',
            'price_group': wholesale
        },
        {
            'name': 'Global Traders',
            'contact_person': 'Michael Brown',
            'phone': '555-246-8101',
            'email': 'michael@globaltraders.com',
            'address': '159 Trading St, Commerce City',
            'price_group': regular
        },
    ]
    
    for client_data in clients_data:
        # Create client account first
        account_name = f"Client: {client_data['name']}"
        account, _ = Account.objects.get_or_create(
            name=account_name,
            defaults={
                'account_type': 'client',
                'currency': usd,
                'initial_balance': Decimal('0.00'),
                'current_balance': Decimal('0.00'),
                'description': f"Account for {client_data['name']}",
                'is_active': True
            }
        )
        
        # Then create client
        Client.objects.get_or_create(
            name=client_data['name'],
            defaults={
                'contact_person': client_data['contact_person'],
                'phone': client_data['phone'],
                'email': client_data['email'],
                'address': client_data['address'],
                'price_group': client_data['price_group'],
                'account': account,
                'is_active': True
            }
        )
    
    # Create Suppliers
    suppliers_data = [
        {
            'name': 'Tech Supplies Inc',
            'contact_person': 'David Lee',
            'phone': '555-888-9999',
            'email': 'david@techsupplies.com',
            'address': '100 Technology Park, Tech City'
        },
        {
            'name': 'Office Essentials',
            'contact_person': 'Lisa Chen',
            'phone': '555-444-3333',
            'email': 'lisa@officeessentials.com',
            'address': '200 Office Blvd, Supply Town'
        },
        {
            'name': 'Food Distributors Ltd',
            'contact_person': 'Mark Wilson',
            'phone': '555-222-1111',
            'email': 'mark@fooddistributors.com',
            'address': '300 Food Lane, Distribution City'
        },
        {
            'name': 'Fabric World',
            'contact_person': 'Sarah Johnson',
            'phone': '555-777-6666',
            'email': 'sarah@fabricworld.com',
            'address': '400 Textile Ave, Material Town'
        }
    ]
    
    for supplier_data in suppliers_data:
        # Create supplier account first
        account_name = f"Supplier: {supplier_data['name']}"
        account, _ = Account.objects.get_or_create(
            name=account_name,
            defaults={
                'account_type': 'supplier',
                'currency': usd,
                'initial_balance': Decimal('0.00'),
                'current_balance': Decimal('0.00'),
                'description': f"Account for {supplier_data['name']}",
                'is_active': True
            }
        )
        
        # Then create supplier
        Supplier.objects.get_or_create(
            name=supplier_data['name'],
            defaults={
                'contact_person': supplier_data['contact_person'],
                'phone': supplier_data['phone'],
                'email': supplier_data['email'],
                'address': supplier_data['address'],
                'account': account,
                'is_active': True
            }
        )

def create_sales():
    print("Creating sales...")
    
    # Get zones, clients, products and admin user
    main_warehouse = Zone.objects.get(name='Main Warehouse')
    downtown_store = Zone.objects.get(name='Downtown Store')
    
    clients = list(Client.objects.all())
    products = list(Product.objects.filter(is_active=True, is_raw_material=False))
    admin_user = User.objects.get(username='admin')
    
    # Generate sales for the past month
    today = timezone.now().date()
    start_date = today - timedelta(days=30)
    
    for i in range(20):  # Create 20 sales
        # Generate random date in the past month
        days_ago = random.randint(0, 30)
        sale_date = today - timedelta(days=days_ago)
        
        # Pick random client and zone
        client = random.choice(clients)
        zone = random.choice([main_warehouse, downtown_store])
        
        # Create sale
        sale_reference = f"S-{timezone.now().strftime('%Y%m')}-{i+1:03d}"
        
        # Calculate random items for this sale (between 1 and 5 items)
        item_count = random.randint(1, 5)
        sale_items = []
        
        # Calculate amounts
        subtotal = Decimal('0.00')
        
        # Generate sale items
        for j in range(item_count):
            product = random.choice(products)
            quantity = Decimal(str(random.randint(1, 10)))
            
            # Apply random discount (0-10%)
            discount_percentage = Decimal(str(random.randint(0, 10)))
            
            unit_price = product.selling_price
            item_total = unit_price * quantity * (Decimal('1.00') - discount_percentage / Decimal('100'))
            
            sale_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_percentage': discount_percentage,
                'total_price': item_total
            })
            
            subtotal += item_total
        
        # Apply tax (e.g., 10%)
        tax_rate = Decimal('0.10')
        tax_amount = subtotal * tax_rate
        
        # Calculate total
        total_amount = subtotal + tax_amount
        
        # Create the sale
        with transaction.atomic():
            sale = Sale.objects.create(
                reference=sale_reference,
                client=client,
                zone=zone,
                date=sale_date,
                status='confirmed',
                subtotal=subtotal,
                discount_amount=Decimal('0.00'),  # No additional discounts
                tax_amount=tax_amount,
                total_amount=total_amount,
                notes=f"Test sale {i+1}",
                created_by=admin_user
            )
            
            # Create sale items
            for item_data in sale_items:
                SaleItem.objects.create(
                    sale=sale,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    discount_percentage=item_data['discount_percentage'],
                    total_price=item_data['total_price']
                )

def create_financial_transactions():
    print("Creating financial transactions...")
    
    # Get accounts
    main_cash = Account.objects.get(name='Main Cash Account')
    bank_account = Account.objects.get(name='Business Bank Account')
    petty_cash = Account.objects.get(name='Petty Cash')
    
    # Get expense categories, payment methods
    expense_categories = list(ExpenseCategory.objects.all())
    payment_methods = list(PaymentMethod.objects.all())
    
    # Get clients and suppliers
    clients = list(Client.objects.all())
    suppliers = list(Supplier.objects.all())
    
    # Get admin user
    admin_user = User.objects.get(username='admin')
    
    # Create expenses
    for i in range(15):  # Create 15 expenses
        category = random.choice(expense_categories)
        payment_method = random.choice(payment_methods)
        account = random.choice([main_cash, bank_account, petty_cash])
        
        # Generate random date in the past month
        days_ago = random.randint(0, 30)
        expense_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Random amount (50-500)
        amount = Decimal(str(random.randint(50, 500)))
        
        # Create expense
        Expense.objects.create(
            reference=f"EXP-{timezone.now().strftime('%Y%m')}-{i+1:03d}",
            category=category,
            account=account,
            date=expense_date,
            amount=amount,
            payment_method=payment_method,
            description=f"Test expense for {category.name}",
            status='paid',
            created_by=admin_user
        )
    
    # Create client payments
    for i in range(10):  # Create 10 client payments
        client = random.choice(clients)
        payment_method = random.choice(payment_methods)
        account = random.choice([main_cash, bank_account])
        
        # Generate random date in the past month
        days_ago = random.randint(0, 30)
        payment_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Random amount (100-1000)
        amount = Decimal(str(random.randint(100, 1000)))
        
        # Create client payment
        ClientPayment.objects.create(
            reference=f"CLIP-{timezone.now().strftime('%Y%m')}-{i+1:03d}",
            client=client,
            account=account,
            date=payment_date,
            amount=amount,
            payment_method=payment_method,
            notes=f"Payment from {client.name}",
            created_by=admin_user
        )
    
    # Create supplier payments
    for i in range(8):  # Create 8 supplier payments
        supplier = random.choice(suppliers)
        payment_method = random.choice(payment_methods)
        account = random.choice([main_cash, bank_account])
        
        # Generate random date in the past month
        days_ago = random.randint(0, 30)
        payment_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Random amount (200-2000)
        amount = Decimal(str(random.randint(200, 2000)))
        
        # Create supplier payment
        SupplierPayment.objects.create(
            reference=f"SUPP-{timezone.now().strftime('%Y%m')}-{i+1:03d}",
            supplier=supplier,
            account=account,
            date=payment_date,
            amount=amount,
            payment_method=payment_method,
            notes=f"Payment to {supplier.name}",
            created_by=admin_user
        )
    
    # Create account transfers
    for i in range(5):  # Create 5 transfers
        # Generate random date in the past month
        days_ago = random.randint(0, 30)
        transfer_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Random amount (500-5000)
        amount = Decimal(str(random.randint(500, 5000)))
        
        # Randomly decide direction of transfer
        if random.choice([True, False]):
            from_account = main_cash
            to_account = bank_account
        else:
            from_account = bank_account
            to_account = petty_cash
        
        # Create transfer
        AccountTransfer.objects.create(
            reference=f"TRF-{timezone.now().strftime('%Y%m')}-{i+1:03d}",
            from_account=from_account,
            to_account=to_account,
            date=transfer_date,
            amount=amount,
            exchange_rate=Decimal('1.00'),  # Same currency
            notes=f"Transfer from {from_account.name} to {to_account.name}",
            created_by=admin_user
        )

def create_stock_data():
    print("Creating stock data...")
    
    # Get zones and products
    main_warehouse = Zone.objects.get(name='Main Warehouse')
    downtown_store = Zone.objects.get(name='Downtown Store')
    north_branch = Zone.objects.get(name='North Branch')
    
    # Get all products
    products = Product.objects.all()
    
    from gestion_api.models import Stock, StockCard, StockSupply, StockSupplyItem
    
    # Create stock entries for each product in each zone
    for product in products:
        # Different quantities per zone
        main_qty = Decimal(str(random.randint(50, 200)))
        downtown_qty = Decimal(str(random.randint(20, 80)))
        north_qty = Decimal(str(random.randint(10, 50)))
        
        # Create or update stock for main warehouse
        Stock.objects.update_or_create(
            product=product,
            zone=main_warehouse,
            defaults={'quantity': main_qty}
        )
        
        # Create or update stock for downtown store
        Stock.objects.update_or_create(
            product=product,
            zone=downtown_store,
            defaults={'quantity': downtown_qty}
        )
        
        # Create or update stock for north branch
        Stock.objects.update_or_create(
            product=product,
            zone=north_branch,
            defaults={'quantity': north_qty}
        )
        
        # Create stock cards (inventory history) for each product
        for zone, qty in [(main_warehouse, main_qty), (downtown_store, downtown_qty), (north_branch, north_qty)]:
            # Initial stock entry
            StockCard.objects.get_or_create(
                product=product,
                zone=zone,
                date=timezone.now().date() - timedelta(days=30),
                transaction_type='supply',
                reference=f"INIT-{product.reference}",
                defaults={
                    'quantity_in': qty,
                    'quantity_out': Decimal('0.00'),
                    'balance': qty,
                    'unit_price': product.purchase_price,
                    'notes': f"Initial stock balance for {product.name}"
                }
            )
    
    # Create some stock supplies (purchases)
    suppliers = Supplier.objects.all()
    admin_user = User.objects.get(username='admin')
    
    for i in range(10):  # Create 10 supply records
        supplier = random.choice(suppliers)
        zone = random.choice([main_warehouse, downtown_store, north_branch])
        
        # Generate random date in the past month
        days_ago = random.randint(5, 25)
        supply_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Create supply record
        supply_reference = f"SUP-{timezone.now().strftime('%Y%m')}-{i+1:03d}"
        
        # Select 1-4 random products for this supply
        selected_products = random.sample(list(products), random.randint(1, 4))
        
        # Calculate totals
        total_amount = Decimal('0.00')
        
        # Create the supply
        with transaction.atomic():
            supply = StockSupply.objects.create(
                reference=supply_reference,
                supplier=supplier,
                zone=zone,
                date=supply_date,
                status=random.choice(['pending', 'partial', 'received']),
                notes=f"Stock supply {i+1}",
                created_by=admin_user
            )
            
            # Create supply items
            for product in selected_products:
                quantity = Decimal(str(random.randint(5, 30)))
                unit_price = product.purchase_price
                total_price = quantity * unit_price
                
                total_amount += total_price
                
                # For received or partial supplies, set a received quantity
                if supply.status in ['received', 'partial']:
                    if supply.status == 'received':
                        received_qty = quantity
                    else:  # partial
                        received_qty = Decimal(str(random.randint(1, int(quantity))))
                else:
                    received_qty = Decimal('0.00')
                
                StockSupplyItem.objects.create(
                    supply=supply,
                    product=product,
                    quantity=quantity,
                    received_quantity=received_qty,
                    unit_price=unit_price,
                    total_price=total_price
                )
                
                # If items were received, create stock card entries
                if received_qty > 0:
                    # Get current stock balance
                    stock = Stock.objects.get(product=product, zone=zone)
                    
                    # Create stock card entry
                    StockCard.objects.create(
                        product=product,
                        zone=zone,
                        date=supply_date,
                        transaction_type='supply',
                        reference=supply_reference,
                        quantity_in=received_qty,
                        quantity_out=Decimal('0.00'),
                        balance=stock.quantity,
                        unit_price=unit_price,
                        notes=f"Received in supply {supply_reference}"
                    )
    
    print("Stock data created successfully!")

def create_transfer_data():
    print("Creating stock transfer data...")
    
    # Get zones and products
    main_warehouse = Zone.objects.get(name='Main Warehouse')
    downtown_store = Zone.objects.get(name='Downtown Store')
    north_branch = Zone.objects.get(name='North Branch')
    
    # Get all products
    products = Product.objects.filter(is_active=True)
    
    from gestion_api.models import StockTransfer, StockTransferItem, StockCard, Stock
    
    # Get admin user
    admin_user = User.objects.get(username='admin')
    
    # Create some transfers between zones
    zone_pairs = [
        (main_warehouse, downtown_store),
        (main_warehouse, north_branch),
        (downtown_store, north_branch)
    ]
    
    for i in range(8):  # Create 8 transfer records
        # Choose random source and destination
        from_zone, to_zone = random.choice(zone_pairs)
        
        # Sometimes flip the direction
        if random.choice([True, False]):
            from_zone, to_zone = to_zone, from_zone
        
        # Generate random date in the past month
        days_ago = random.randint(2, 20)
        transfer_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Create transfer record
        transfer_reference = f"TRF-{timezone.now().strftime('%Y%m')}-{i+1:03d}"
        
        # Select 1-3 random products for this transfer
        selected_products = random.sample(list(products), random.randint(1, 3))
        
        # Create the transfer
        with transaction.atomic():
            transfer = StockTransfer.objects.create(
                reference=transfer_reference,
                from_zone=from_zone,
                to_zone=to_zone,
                date=transfer_date,
                status=random.choice(['pending', 'partial', 'completed']),
                notes=f"Stock transfer {i+1}",
                created_by=admin_user
            )
            
            # Create transfer items
            for product in selected_products:
                # Get current stock in source zone
                try:
                    source_stock = Stock.objects.get(product=product, zone=from_zone)
                    if source_stock.quantity <= 0:
                        continue  # Skip if no stock available
                        
                    # Transfer amount (up to 50% of available stock)
                    max_transfer = int(source_stock.quantity / 2) + 1
                    quantity = Decimal(str(random.randint(1, max_transfer)))
                    
                    # For completed or partial transfers, set a transferred quantity
                    if transfer.status in ['completed', 'partial']:
                        if transfer.status == 'completed':
                            transferred_qty = quantity
                        else:  # partial
                            transferred_qty = Decimal(str(random.randint(1, int(quantity))))
                    else:
                        transferred_qty = Decimal('0.00')
                    
                    StockTransferItem.objects.create(
                        transfer=transfer,
                        product=product,
                        quantity=quantity,
                        transferred_quantity=transferred_qty
                    )
                    
                    # If items were transferred, update stock and create stock card entries
                    if transferred_qty > 0:
                        # Update source zone stock (decrease)
                        source_stock.quantity -= transferred_qty
                        source_stock.save()
                        
                        # Update or create destination zone stock (increase)
                        dest_stock, created = Stock.objects.get_or_create(
                            product=product, 
                            zone=to_zone,
                            defaults={'quantity': transferred_qty}
                        )
                        
                        if not created:
                            dest_stock.quantity += transferred_qty
                            dest_stock.save()
                        
                        # Create source stock card entry (out)
                        StockCard.objects.create(
                            product=product,
                            zone=from_zone,
                            date=transfer_date,
                            transaction_type='transfer_out',
                            reference=transfer_reference,
                            quantity_in=Decimal('0.00'),
                            quantity_out=transferred_qty,
                            balance=source_stock.quantity,
                            unit_price=product.purchase_price,
                            notes=f"Transferred to {to_zone.name}"
                        )
                        
                        # Create destination stock card entry (in)
                        StockCard.objects.create(
                            product=product,
                            zone=to_zone,
                            date=transfer_date,
                            transaction_type='transfer_in',
                            reference=transfer_reference,
                            quantity_in=transferred_qty,
                            quantity_out=Decimal('0.00'),
                            balance=dest_stock.quantity,
                            unit_price=product.purchase_price,
                            notes=f"Transferred from {from_zone.name}"
                        )
                        
                except Stock.DoesNotExist:
                    continue  # Skip if product doesn't have stock in source zone
    
    print("Stock transfer data created successfully!")

def create_inventory_data():
    print("Creating inventory count data...")
    
    # Get zones and products
    main_warehouse = Zone.objects.get(name='Main Warehouse')
    downtown_store = Zone.objects.get(name='Downtown Store')
    north_branch = Zone.objects.get(name='North Branch')
    
    zones = [main_warehouse, downtown_store, north_branch]
    
    from gestion_api.models import Inventory, InventoryItem, StockCard, Stock
    
    # Get admin user
    admin_user = User.objects.get(username='admin')
    
    # Create inventory counts for each zone
    for i, zone in enumerate(zones):
        # Generate random date in the past month
        days_ago = random.randint(1, 15)
        inventory_date = timezone.now().date() - timedelta(days=days_ago)
        
        # Create inventory record
        inventory_reference = f"INV-{zone.name[:3].upper()}-{timezone.now().strftime('%Y%m')}"
        
        # Get products with stock in this zone
        zone_stocks = Stock.objects.filter(zone=zone, quantity__gt=0)
        
        if not zone_stocks.exists():
            continue
            
        # Randomize inventory status
        status = random.choice(['draft', 'in_progress', 'completed'])
        
        # Create the inventory
        with transaction.atomic():
            inventory = Inventory.objects.create(
                reference=inventory_reference,
                zone=zone,
                date=inventory_date,
                status=status,
                notes=f"Inventory count for {zone.name}",
                created_by=admin_user
            )
            
            # Create inventory items (for all products in this zone)
            for stock in zone_stocks:
                product = stock.product
                expected_qty = stock.quantity
                
                # Randomize the actual counted quantity (usually close to expected, sometimes off)
                variance_percent = Decimal(str(random.uniform(-0.1, 0.1)))  # -10% to +10%
                variance = expected_qty * variance_percent
                actual_qty = expected_qty + variance
                actual_qty = max(0, actual_qty.quantize(Decimal('0.01')))
                
                # Calculate difference
                difference = actual_qty - expected_qty
                
                InventoryItem.objects.create(
                    inventory=inventory,
                    product=product,
                    expected_quantity=expected_qty,
                    actual_quantity=actual_qty,
                    difference=difference,
                    notes=f"Stock count for {product.name}"
                )
                
                # If inventory is completed, adjust stock and create stock card entry for differences
                if status == 'completed' and difference != 0:
                    # Update stock
                    stock.quantity = actual_qty
                    stock.save()
                    
                    # Create stock card entry for the adjustment
                    transaction_type = 'inventory'
                    quantity_in = abs(difference) if difference > 0 else Decimal('0.00')
                    quantity_out = abs(difference) if difference < 0 else Decimal('0.00')
                    
                    StockCard.objects.create(
                        product=product,
                        zone=zone,
                        date=inventory_date,
                        transaction_type=transaction_type,
                        reference=inventory_reference,
                        quantity_in=quantity_in,
                        quantity_out=quantity_out,
                        balance=actual_qty,
                        unit_price=product.purchase_price,
                        notes=f"Inventory adjustment: {'surplus' if difference > 0 else 'shortage'} of {abs(difference)}"
                    )
    
    print("Inventory data created successfully!")

def create_sale_stock_entries():
    print("Creating stock entries for existing sales...")
    
    from gestion_api.models import Stock, StockCard
    
    # Get all confirmed sales
    sales = Sale.objects.filter(status='confirmed')
    
    for sale in sales:
        # Process each sale item
        for item in sale.items.all():
            product = item.product
            zone = sale.zone
            quantity = item.quantity
            
            try:
                # Get stock for this product in this zone
                stock = Stock.objects.get(product=product, zone=zone)
                
                # Skip if not enough stock (this is demo data, so we'll be lenient)
                if stock.quantity < quantity:
                    continue
                
                # Update stock quantity
                stock.quantity -= quantity
                stock.save()
                
                # Create stock card entry for the sale
                StockCard.objects.create(
                    product=product,
                    zone=zone,
                    date=sale.date,
                    transaction_type='sale',
                    reference=sale.reference,
                    quantity_in=Decimal('0.00'),
                    quantity_out=quantity,
                    balance=stock.quantity,
                    unit_price=item.unit_price,
                    notes=f"Sale to {sale.client.name}"
                )
                
            except Stock.DoesNotExist:
                # Skip if product doesn't have stock in this zone
                continue
    
    print("Sale stock entries created successfully!")

def run_seeds():
    """Run all seed functions"""
    print("Creating permission groups...")
    groups = create_permissions()
    
    print("Creating demo users...")
    create_users(groups)
    
    print("Creating reference data...")
    create_reference_data()
    
    print("Creating accounts...")
    create_accounts()
    
    print("Creating products...")
    create_products()
    
    print("Creating clients and suppliers...")
    create_clients_suppliers()
    
    print("Creating sales...")
    create_sales()
    
    print("Creating financial transactions...")
    create_financial_transactions()
    
    print("Creating stock data...")
    create_stock_data()
    
    print("Creating stock transfer data...")
    create_transfer_data()
    
    print("Creating inventory count data...")
    create_inventory_data()
    
    print("Creating stock entries for sales...")
    create_sale_stock_entries()
    
    print("Seed data completed successfully!")

if __name__ == "__main__":
    run_seeds()
