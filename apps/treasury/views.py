from decimal import Decimal
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
                outstanding_sales = Sale.objects.filter(
                    client__account=account,
                    payment_status__in=['pending_paiement','unpaid', 'partially_paid']
                ).values('id', 'reference', 'total_amount', 'paid_amount', 'date', 'status', 'remaining_amount')
                response_data['outstanding_sales'] = list(outstanding_sales)
            else:  # supplier
                from apps.inventory.models import StockSupply
                outstanding_supplies = StockSupply.objects.filter(
                    supplier__account=account,
                    payment_status__in=['unpaid', 'partially_paid']
                ).values('id', 'reference', 'total_amount', 'paid_amount', 'date', 'status', 'remaining_amount')
                response_data['outstanding_supplies'] = list(outstanding_supplies)
            
            return Response(response_data)
            
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
