from decimal import Decimal
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import (
    Account, Expense, ClientPayment, SupplierPayment, AccountTransfer,
    CashReceipt, SupplierCashPayment, AccountStatement
)
from .serializers import (
    AccountSerializer, ExpenseSerializer, ClientPaymentSerializer, SupplierPaymentSerializer,
    AccountTransferSerializer, CashReceiptSerializer, SupplierCashPaymentSerializer,
    AccountStatementSerializer
)


class AccountViewSet(viewsets.ModelViewSet):
    """API endpoint for accounts"""
    queryset = Account.objects.all().order_by('name')
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get accounts filtered by type"""
        account_type = request.query_params.get('type')
        if not account_type:
            return Response({'error': 'type parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        accounts = self.queryset.filter(account_type=account_type)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    """API endpoint for expenses"""
    queryset = Expense.objects.all().order_by('-date')
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ClientPaymentViewSet(viewsets.ModelViewSet):
    """API endpoint for client payments"""
    queryset = ClientPayment.objects.all().order_by('-date')
    serializer_class = ClientPaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """API endpoint for supplier payments"""
    queryset = SupplierPayment.objects.all().order_by('-date')
    serializer_class = SupplierPaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AccountTransferViewSet(viewsets.ModelViewSet):
    """API endpoint for account transfers"""
    queryset = AccountTransfer.objects.all().order_by('-date')
    serializer_class = AccountTransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CashReceiptViewSet(viewsets.ModelViewSet):
    """API endpoint for cash receipts"""
    queryset = CashReceipt.objects.all().order_by('-date')
    serializer_class = CashReceiptSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Set allocated_amount to the amount value if not provided
        if 'allocated_amount' not in serializer.validated_data or serializer.validated_data['allocated_amount'] is None:
            serializer.validated_data['allocated_amount'] = serializer.validated_data.get('amount', 0)
        
        # Save the cash receipt
        cash_receipt = serializer.save(created_by=self.request.user)
        
        try:
            client_name = cash_receipt.client.name if cash_receipt.client else 'Client non spécifié'
            # Get the last statement for this account
            last_statement = AccountStatement.objects.filter(
                account=cash_receipt.account
            ).order_by('-date', '-id').first()
            previous_balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')
            # Calculate new balance
            new_balance = previous_balance + Decimal(str(cash_receipt.amount))
            # Create AccountStatement entry
            AccountStatement.objects.create(
                account=cash_receipt.account,
                date=cash_receipt.date,
                reference=cash_receipt.reference,
                transaction_type='cash_receipt',
                description=f"Dépôt client: {client_name} - {cash_receipt.description}",
                credit=cash_receipt.amount,
                debit=0,
                balance=new_balance
            )
            # Update the account's current_balance
            account = cash_receipt.account
            account.current_balance = new_balance
            account.save(update_fields=['current_balance'])
        except Exception as e:
            print(f"Error creating AccountStatement for CashReceipt {cash_receipt.id}: {e}")


class SupplierCashPaymentViewSet(viewsets.ModelViewSet):
    """API endpoint for supplier cash payments"""
    queryset = SupplierCashPayment.objects.all().order_by('-date')
    serializer_class = SupplierCashPaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AccountStatementViewSet(viewsets.ModelViewSet):
    """API endpoint for account statements"""
    queryset = AccountStatement.objects.all().order_by('-date')
    serializer_class = AccountStatementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter account statements by account if provided"""
        queryset = AccountStatement.objects.all().order_by('-date')
        account_id = self.request.query_params.get('account', None)
        if account_id is not None:
            try:
                queryset = queryset.filter(account_id=account_id)
            except ValueError:
                queryset = AccountStatement.objects.none()
        return queryset

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get current balance for an account"""
        account_id = request.query_params.get('account_id')
        
        if account_id:
            try:
                account = Account.objects.get(id=account_id)
                last_statement = AccountStatement.objects.filter(account=account).order_by('-date', '-id').first()
                balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')
                
                return Response({
                    'account_id': account.id,
                    'account_name': account.name,
                    'balance': balance
                })
            except Account.DoesNotExist:
                return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'account_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def account_info(self, request):
        """Get account info with balance, statements, and outstanding sales/supplies"""
        account_id = request.query_params.get('account_id')
        entity_type = request.query_params.get('type')  # 'client' or 'supplier'
        
        if not account_id:
            return Response({'error': 'account_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not entity_type or entity_type not in ['client', 'supplier']:
            return Response({'error': 'type parameter must be "client" or "supplier"'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            account = Account.objects.get(id=account_id)
            
            # Get account balance
            last_statement = AccountStatement.objects.filter(account=account).order_by('-date', '-id').first()
            balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')
            
            # Get account statements
            statements = AccountStatement.objects.filter(account=account).order_by('-date', '-id')
            statement_serializer = AccountStatementSerializer(statements, many=True)
            
            response_data = {
                'balance': balance,
                'statements': statement_serializer.data,
            }
            
            # Get outstanding sales or supplies based on entity type
            if entity_type == 'client':
                from apps.sales.models import Sale
                from apps.partners.models import Client
                
                # Get client associated with this account
                client = Client.objects.filter(account=account).first()
                
                if client:
                    # Calculate total sales (all sales for this client)
                    all_sales = Sale.objects.filter(client=client)
                    total_sales = sum(sale.total_amount for sale in all_sales)
                    
                    # Calculate total payments from account (sum of all credits in account statements from sales)
                    sale_payments = AccountStatement.objects.filter(
                        account=account,
                        transaction_type__in=['sale', 'client_payment']
                    ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
                    
                    # Calculate total account credits (deposits/cash receipts)
                    total_credits = AccountStatement.objects.filter(
                        account=account,
                        transaction_type='cash_receipt'
                    ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
                    
                    response_data.update({
                        'client_id': client.id,
                        'client_name': client.name,
                        'total_sales': total_sales,
                        'total_account_credits': total_credits,
                        'sale_payments_from_account': sale_payments,
                        'sales_count': all_sales.count(),
                        'payments_count': AccountStatement.objects.filter(
                            account=account,
                            transaction_type__in=['sale', 'client_payment', 'cash_receipt']
                        ).count(),
                    })
                
                outstanding_sales = Sale.objects.filter(
                    client__account=account,
                    payment_status__in=['pending_paiement','unpaid', 'partially_paid']
                ).values('id', 'reference', 'total_amount', 'paid_amount', 'date', 'status', 'remaining_amount')
                response_data['outstanding_sales'] = list(outstanding_sales)
            else:  # supplier
                from apps.inventory.models import StockSupply
                from apps.partners.models import Supplier
                
                # Get supplier associated with this account
                supplier = Supplier.objects.filter(account=account).first()
                
                if supplier:
                    # Calculate total purchases (all supplies for this supplier)
                    all_supplies = StockSupply.objects.filter(supplier=supplier)
                    total_purchases = sum(supply.total_amount for supply in all_supplies)
                    
                    # Calculate total payments from account
                    purchase_payments = AccountStatement.objects.filter(
                        account=account,
                        transaction_type__in=['supply', 'supplier_payment']
                    ).aggregate(total=models.Sum('debit'))['total'] or Decimal('0.00')
                    
                    # Calculate total account credits (cash payments)
                    total_credits = AccountStatement.objects.filter(
                        account=account,
                        transaction_type='supplier_cash_payment'
                    ).aggregate(total=models.Sum('credit'))['total'] or Decimal('0.00')
                    
                    response_data.update({
                        'supplier_id': supplier.id,
                        'supplier_name': supplier.name,
                        'total_purchases': total_purchases,
                        'total_account_credits': total_credits,
                        'purchase_payments_from_account': purchase_payments,
                        'purchases_count': all_supplies.count(),
                        'payments_count': AccountStatement.objects.filter(
                            account=account,
                            transaction_type__in=['supply', 'supplier_payment', 'supplier_cash_payment']
                        ).count(),
                    })
                
                outstanding_supplies = StockSupply.objects.filter(
                    supplier__account=account,
                    payment_status__in=['unpaid', 'partially_paid']
                ).values('id', 'reference', 'total_amount', 'paid_amount', 'date', 'status', 'remaining_amount')
                response_data['outstanding_supplies'] = list(outstanding_supplies)
            
            return Response(response_data)
            
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
