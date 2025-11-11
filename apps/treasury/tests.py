"""
Tests for Treasury app - Account, CashReceipt, AccountStatement, Payments
"""
import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from datetime import date

from apps.treasury.models import (
    Account, CashReceipt, AccountStatement, Expense,
    AccountTransfer, SupplierCashPayment
)


# ============= Account Model Tests =============

@pytest.mark.django_db
class TestAccountModel:
    """Test Account model"""
    
    def test_account_creation(self, account):
        """Test creating an account"""
        assert account.id is not None
        assert account.name == "Main Cash Account"
        assert account.account_type == 'cash'
        assert account.current_balance == Decimal('50000.00')
    
    def test_account_types(self, db, currency):
        """Test different account types"""
        cash_account = Account.objects.create(
            name="Cash",
            account_type='cash',
            currency=currency,
            current_balance=Decimal('10000.00')
        )
        bank_account = Account.objects.create(
            name="Bank",
            account_type='bank',
            currency=currency,
            current_balance=Decimal('50000.00')
        )
        
        assert cash_account.account_type == 'cash'
        assert bank_account.account_type == 'bank'
    
    def test_account_str_representation(self, account):
        """Test string representation"""
        assert "Main Cash Account" in str(account)
        assert "Caisse" in str(account)
    
    def test_account_balance_update(self, account):
        """Test updating account balance"""
        initial_balance = account.current_balance
        account.current_balance += Decimal('5000.00')
        account.save()
        account.refresh_from_db()
        assert account.current_balance == initial_balance + Decimal('5000.00')


# ============= CashReceipt Model Tests =============

@pytest.mark.django_db
class TestCashReceiptModel:
    """Test CashReceipt model for customer payments"""
    
    def test_cash_receipt_creation(self, db, account, client_partner, payment_method):
        """Test creating a cash receipt"""
        receipt = CashReceipt.objects.create(
            account=account,
            client=client_partner,
            date=date.today(),
            amount=Decimal('1000.00'),
            allocated_amount=Decimal('1000.00'),
            payment_method=payment_method,
            description="Payment for services"
        )
        assert receipt.id is not None
        assert receipt.amount == Decimal('1000.00')
        assert receipt.client == client_partner
    
    def test_cash_receipt_with_sale(self, db, account, sale, client_partner, payment_method):
        """Test cash receipt linked to a sale"""
        receipt = CashReceipt.objects.create(
            account=account,
            sale=sale,
            client=client_partner,
            date=date.today(),
            amount=sale.total_amount,
            allocated_amount=sale.total_amount,
            payment_method=payment_method
        )
        assert receipt.sale == sale
        assert receipt.allocated_amount == sale.total_amount
    
    def test_partial_allocation(self, db, account, client_partner, payment_method):
        """Test partial allocation of payment"""
        receipt = CashReceipt.objects.create(
            account=account,
            client=client_partner,
            date=date.today(),
            amount=Decimal('1000.00'),
            allocated_amount=Decimal('750.00'),
            payment_method=payment_method
        )
        unallocated = receipt.amount - receipt.allocated_amount
        assert unallocated == Decimal('250.00')


# ============= AccountStatement Model Tests =============

@pytest.mark.django_db
class TestAccountStatementModel:
    """Test AccountStatement for tracking transactions"""
    
    def test_statement_creation(self, db, account):
        """Test creating an account statement entry"""
        statement = AccountStatement.objects.create(
            account=account,
            date=date.today(),
            transaction_type='cash_receipt',
            reference='REC-001',
            description='Customer payment',
            debit=Decimal('0.00'),
            credit=Decimal('5000.00'),
            balance=account.current_balance + Decimal('5000.00')
        )
        assert statement.id is not None
        assert statement.credit == Decimal('5000.00')
        assert statement.debit == Decimal('0.00')
    
    def test_statement_debit_transaction(self, db, account):
        """Test debit transaction"""
        statement = AccountStatement.objects.create(
            account=account,
            date=date.today(),
            transaction_type='expense',
            reference='EXP-001',
            description='Office supplies',
            debit=Decimal('2000.00'),
            credit=Decimal('0.00'),
            balance=account.current_balance - Decimal('2000.00')
        )
        assert statement.debit == Decimal('2000.00')
        assert statement.balance < account.current_balance
    
    def test_statement_ordering(self, db, account):
        """Test statement ordering by date"""
        stmt1 = AccountStatement.objects.create(
            account=account,
            date=date.today(),
            transaction_type='deposit',
            reference='DEP-001',
            debit=Decimal('0.00'),
            credit=Decimal('1000.00'),
            balance=account.current_balance + Decimal('1000.00')
        )
        stmt2 = AccountStatement.objects.create(
            account=account,
            date=date.today(),
            transaction_type='expense',
            reference='EXP-001',
            debit=Decimal('500.00'),
            credit=Decimal('0.00'),
            balance=account.current_balance + Decimal('500.00')
        )
        
        statements = AccountStatement.objects.filter(account=account).order_by('-date')
        assert statements.count() >= 2


# ============= Expense Model Tests =============

@pytest.mark.django_db
class TestExpenseModel:
    """Test Expense model"""
    
    def test_expense_creation(self, db, account, payment_method):
        """Test creating an expense"""
        from apps.app_settings.models import ExpenseCategory
        category = ExpenseCategory.objects.create(name="Office Supplies")
        
        expense = Expense.objects.create(
            reference='EXP-2025-001',
            category=category,
            account=account,
            date=date.today(),
            amount=Decimal('5000.00'),
            description='Printer and paper',
            payment_method=payment_method,
            status='pending'
        )
        assert expense.id is not None
        assert expense.amount == Decimal('5000.00')
        assert expense.status == 'pending'
    
    def test_expense_approval(self, db, account, payment_method):
        """Test expense approval workflow"""
        from apps.app_settings.models import ExpenseCategory
        category = ExpenseCategory.objects.create(name="Transport")
        
        expense = Expense.objects.create(
            reference='EXP-2025-002',
            category=category,
            account=account,
            date=date.today(),
            amount=Decimal('3000.00'),
            description='Fuel',
            payment_method=payment_method,
            status='draft'
        )
        
        # Approve expense
        expense.status = 'approved'
        expense.save()
        assert expense.status == 'approved'
        
        # Mark as paid
        expense.status = 'paid'
        expense.save()
        assert expense.status == 'paid'


# ============= AccountTransfer Model Tests =============

@pytest.mark.django_db
class TestAccountTransferModel:
    """Test account transfers"""
    
    def test_account_transfer(self, db, currency):
        """Test transferring between accounts"""
        account1 = Account.objects.create(
            name="Cash Account",
            account_type='cash',
            currency=currency,
            current_balance=Decimal('10000.00')
        )
        account2 = Account.objects.create(
            name="Bank Account",
            account_type='bank',
            currency=currency,
            current_balance=Decimal('50000.00')
        )
        
        transfer = AccountTransfer.objects.create(
            reference='TRF-001',
            from_account=account1,
            to_account=account2,
            date=date.today(),
            amount=Decimal('5000.00'),
            exchange_rate=Decimal('1.00')
        )
        
        assert transfer.id is not None
        assert transfer.amount == Decimal('5000.00')
        assert transfer.from_account == account1
        assert transfer.to_account == account2


# ============= Account API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestAccountAPI:
    """Test Account API endpoints"""
    
    def test_list_accounts(self, authenticated_client, account):
        """Test listing accounts"""
        url = reverse('account-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_account(self, admin_client, currency):
        """Test creating an account via API"""
        url = reverse('account-list')
        data = {
            'name': 'New Bank Account',
            'account_type': 'bank',
            'currency': currency.id,
            'initial_balance': '25000.00',
            'current_balance': '25000.00',
            'is_active': True
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Bank Account'
    
    def test_retrieve_account(self, authenticated_client, account):
        """Test retrieving specific account"""
        url = reverse('account-detail', kwargs={'pk': account.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == account.name
    
    def test_update_account_balance(self, admin_client, account):
        """Test updating account balance"""
        url = reverse('account-detail', kwargs={'pk': account.id})
        new_balance = Decimal('60000.00')
        data = {
            'name': account.name,
            'account_type': account.account_type,
            'currency': account.currency.id,
            'current_balance': str(new_balance),
            'is_active': True
        }
        response = admin_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        account.refresh_from_db()
        assert account.current_balance == new_balance


# ============= CashReceipt API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestCashReceiptAPI:
    """Test CashReceipt API endpoints"""
    
    def test_list_cash_receipts(self, authenticated_client, db, account, client_partner, payment_method):
        """Test listing cash receipts"""
        CashReceipt.objects.create(
            account=account,
            client=client_partner,
            date=date.today(),
            amount=Decimal('1000.00'),
            allocated_amount=Decimal('1000.00'),
            payment_method=payment_method
        )
        
        url = reverse('cashreceipt-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_cash_receipt(self, admin_client, account, client_partner, payment_method):
        """Test creating a cash receipt via API"""
        url = reverse('cashreceipt-list')
        data = {
            'account': account.id,
            'client': client_partner.id,
            'date': date.today().isoformat(),
            'amount': '2500.00',
            'allocated_amount': '2500.00',
            'payment_method': payment_method.id,
            'description': 'Payment received'
        }
        response = admin_client.post(url, data, format='json')
        # Debug: print response if test fails
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        assert response.status_code == status.HTTP_201_CREATED
        assert 'reference' in response.data
        # Verify reference was auto-generated
        assert response.data['reference'].startswith('ENC-')


# ============= Integration Tests =============

@pytest.mark.django_db
@pytest.mark.integration
class TestTreasuryIntegration:
    """Integration tests for treasury operations"""
    
    def test_complete_payment_flow(self, db, account, sale, client_partner, payment_method):
        """Test complete payment flow with account statements"""
        initial_balance = account.current_balance
        
        # Create cash receipt
        receipt = CashReceipt.objects.create(
            account=account,
            sale=sale,
            client=client_partner,
            date=date.today(),
            amount=sale.total_amount,
            allocated_amount=sale.total_amount,
            payment_method=payment_method
        )
        
        # Update account balance
        new_balance = initial_balance + receipt.allocated_amount
        account.current_balance = new_balance
        account.save()
        
        # Create account statement
        statement = AccountStatement.objects.create(
            account=account,
            date=date.today(),
            transaction_type='cash_receipt',
            reference=receipt.reference,
            description=f"Payment from {client_partner.name}",
            debit=Decimal('0.00'),
            credit=receipt.allocated_amount,
            balance=new_balance
        )
        
        # Verify everything
        account.refresh_from_db()
        assert account.current_balance == new_balance
        assert AccountStatement.objects.filter(account=account).exists()
    
    def test_account_transfer_flow(self, db, currency):
        """Test complete account transfer flow"""
        account1 = Account.objects.create(
            name="Cash",
            account_type='cash',
            currency=currency,
            current_balance=Decimal('20000.00')
        )
        account2 = Account.objects.create(
            name="Bank",
            account_type='bank',
            currency=currency,
            current_balance=Decimal('100000.00')
        )
        
        transfer_amount = Decimal('5000.00')
        
        # Create transfer
        transfer = AccountTransfer.objects.create(
            reference='TRF-001',
            from_account=account1,
            to_account=account2,
            date=date.today(),
            amount=transfer_amount,
            exchange_rate=Decimal('1.00')
        )
        
        # Update balances
        account1.current_balance -= transfer_amount
        account1.save()
        account2.current_balance += transfer_amount
        account2.save()
        
        # Create statements
        AccountStatement.objects.create(
            account=account1,
            date=date.today(),
            transaction_type='transfer_out',
            reference=transfer.reference,
            debit=transfer_amount,
            credit=Decimal('0.00'),
            balance=account1.current_balance
        )
        AccountStatement.objects.create(
            account=account2,
            date=date.today(),
            transaction_type='transfer_in',
            reference=transfer.reference,
            debit=Decimal('0.00'),
            credit=transfer_amount,
            balance=account2.current_balance
        )
        
        # Verify
        account1.refresh_from_db()
        account2.refresh_from_db()
        assert account1.current_balance == Decimal('15000.00')
        assert account2.current_balance == Decimal('105000.00')
