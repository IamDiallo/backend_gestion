# Backend Testing Guide

## Overview

This project uses **pytest** for testing with comprehensive test coverage across all Django apps.

## Test Structure

```
backend/
├── conftest.py                    # Shared fixtures and factories
├── pytest.ini                     # Pytest configuration
└── apps/
    ├── core/tests.py             # Core app tests (Auth, Users, Zones)
    ├── sales/tests.py            # Sales app tests (Sales, Quotes, Invoices)
    ├── inventory/tests.py        # Inventory app tests (Products, Stock)
    ├── treasury/tests.py         # Treasury app tests (Accounts, Payments)
    └── partners/tests.py         # Partners app tests (Clients, Suppliers)
```

## Installation

Install testing dependencies:

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- pytest
- pytest-django
- pytest-cov
- factory-boy
- faker

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests for a specific app
```bash
pytest apps/sales/tests.py
pytest apps/inventory/tests.py
pytest apps/core/tests.py
```

### Run tests with coverage report
```bash
pytest --cov=apps --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

### Run tests with verbose output
```bash
pytest -v
```

### Run only unit tests
```bash
pytest -m unit
```

### Run only API tests
```bash
pytest -m api
```

### Run only integration tests
```bash
pytest -m integration
```

### Run tests matching a pattern
```bash
pytest -k "test_sale"
pytest -k "test_client or test_supplier"
```

### Run tests and stop on first failure
```bash
pytest -x
```

### Run failed tests from last run
```bash
pytest --lf
```

## Test Markers

Tests are organized with the following markers:

- `@pytest.mark.unit` - Unit tests (isolated model/function tests)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.slow` - Slow-running tests

## Test Coverage by App

### Core App Tests
- User and UserProfile model tests
- Zone model tests
- JWT Authentication (token obtain, refresh, verify)
- Permission system tests
- Zone API endpoints

### Sales App Tests
- Sale model (creation, cancellation, deletion)
- SaleItem model
- Sale status transitions
- Stock restoration on cancellation
- Quote model and reference generation
- Payment tracking
- Sale API endpoints with filtering

### Inventory App Tests
- Product model and reference generation
- Stock model and unique constraints
- StockCard transaction tracking
- Stock transfers between zones
- Product API endpoints
- Stock filtering and low stock alerts
- Complete stock flow (supply → sale → return)

### Treasury App Tests
- Account model (all types: cash, bank, client, supplier)
- CashReceipt model
- AccountStatement tracking
- Expense model and approval workflow
- Account transfers
- Payment flows with statements
- Treasury API endpoints

### Partners App Tests
- Client model CRUD operations
- Supplier model CRUD operations
- Client/Supplier API endpoints
- Search and filtering
- Integration with sales and supplies
- Account balance tracking

## Fixtures Available

Common fixtures (defined in `conftest.py`):

- `api_client` - DRF API client
- `authenticated_client` - Authenticated user API client
- `admin_client` - Admin user API client
- `admin_user` - Admin user instance
- `regular_user` - Regular user instance
- `zone` - Test zone
- `user_profile` - User profile with role
- `currency` - Test currency (GNF)
- `unit_of_measure` - Test unit (kg)
- `product_category` - Test category
- `payment_method` - Test payment method
- `client_partner` - Test client
- `supplier_partner` - Test supplier
- `product` - Test product
- `stock` - Test stock entry
- `account` - Test account
- `sale` - Test sale
- `sale_with_items` - Sale with items

## Factories

Use factories to create test data easily:

```python
from conftest import UserFactory, ProductFactory, SaleFactory

# Create test data
user = UserFactory(username='testuser')
product = ProductFactory(name='Test Product', selling_price=Decimal('100.00'))
sale = SaleFactory(client=client, zone=zone)
```

## Writing New Tests

### Model Test Example
```python
@pytest.mark.django_db
class TestYourModel:
    def test_model_creation(self, fixture):
        """Test creating a model instance"""
        instance = YourModel.objects.create(name="Test")
        assert instance.id is not None
        assert instance.name == "Test"
```

### API Test Example
```python
@pytest.mark.django_db
@pytest.mark.api
class TestYourAPI:
    def test_list_endpoint(self, authenticated_client):
        """Test listing items"""
        url = reverse('yourmodel-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
```

### Integration Test Example
```python
@pytest.mark.django_db
@pytest.mark.integration
class TestYourIntegration:
    def test_complete_workflow(self, db, fixture1, fixture2):
        """Test complete workflow"""
        # Test logic here
        assert result == expected
```

## Continuous Integration

Tests should be run in CI/CD pipeline before deployment:

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: |
    cd backend
    pytest --cov=apps --cov-report=xml
```

## Tips

1. **Use fixtures** - Reuse common test data via fixtures
2. **Mark tests** - Use markers to organize and selectively run tests
3. **Test isolation** - Each test should be independent
4. **Descriptive names** - Test names should describe what they test
5. **Coverage goals** - Aim for >80% code coverage
6. **Fast tests** - Keep tests fast; mark slow tests with `@pytest.mark.slow`

## Common Commands Cheat Sheet

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html --cov-report=term

# Run specific test file
pytest apps/sales/tests.py

# Run specific test class
pytest apps/sales/tests.py::TestSaleModel

# Run specific test method
pytest apps/sales/tests.py::TestSaleModel::test_sale_creation

# Run with markers
pytest -m api                    # Only API tests
pytest -m "not slow"             # Exclude slow tests
pytest -m "unit or integration"  # Multiple markers

# Debugging
pytest -v                        # Verbose
pytest -s                        # Show print statements
pytest -x                        # Stop on first failure
pytest --pdb                     # Drop into debugger on failure

# Coverage
pytest --cov=apps --cov-report=html    # HTML report
pytest --cov=apps --cov-report=term    # Terminal report
pytest --cov=apps --cov-report=xml     # XML (for CI)
```

## Troubleshooting

### Database errors
Make sure your test database settings are correct in `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_db',
        # ... other settings
    }
}
```

### Import errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Fixture not found
Check that fixtures are defined in `conftest.py` or imported properly.

## Next Steps

1. Run the full test suite: `pytest`
2. Check coverage: `pytest --cov=apps --cov-report=html`
3. Add tests for any uncovered code
4. Integrate tests into CI/CD pipeline
5. Set up pre-commit hooks to run tests

## Support

For issues or questions about testing, refer to:
- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
