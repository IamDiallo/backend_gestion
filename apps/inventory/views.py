from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.utils import timezone
from django.db import transaction
import qrcode
import io
from django.http import HttpResponse
from decimal import Decimal
from django.db.models import Sum, Q

from .models import (
    Product, Stock, StockSupply, StockCard,
    StockTransfer, Inventory, StockReturn
)
from .serializers import (
    ProductSerializer,
    StockSerializer,
    StockSupplySerializer,
    StockCardSerializer,
    StockTransferSerializer,
    InventorySerializer,
    StockReturnSerializer
)
from apps.inventory.models import Product, Stock, StockSupply, StockCard
from apps.treasury.models import Account, SupplierCashPayment, AccountStatement,SupplierCashPayment
from apps.partners.models import Supplier
class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products"""
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Generate QR code for product"""
        
        product = self.get_object()
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"Product: {product.name} - Reference: {product.reference}")
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Return as image response
        return HttpResponse(buffer.getvalue(), content_type='image/png')


class StockViewSet(viewsets.ModelViewSet):
    """API endpoint for stock"""
    queryset = Stock.objects.all().order_by('product__name')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock levels"""
        low_stock = self.queryset.filter(
            quantity__lt=F('product__min_stock_level'),
            product__min_stock_level__gt=0
        )
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check_availability(self, request):
        """
        Check stock availability for a product in a specific zone
        Query Parameters:
        - product: Product ID (required)
        - zone: Zone ID (required)
        - quantity: Quantity to check (required)
        
        Returns:
        - available: Boolean indicating if stock is available
        - current_stock: Current stock quantity
        - requested_quantity: Requested quantity
        - shortfall: Amount short (0 if available)
        """
        product_id = request.query_params.get('product')
        zone_id = request.query_params.get('zone')
        quantity = request.query_params.get('quantity')
        
        # Validate parameters
        if not product_id:
            return Response(
                {'error': 'product parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not zone_id:
            return Response(
                {'error': 'zone parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not quantity:
            return Response(
                {'error': 'quantity parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            requested_quantity = float(quantity)
        except ValueError:
            return Response(
                {'error': 'quantity must be a valid number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if stock exists for this product and zone
        try:
            stock = Stock.objects.get(product_id=product_id, zone_id=zone_id)
            current_stock = float(stock.quantity)
            available = current_stock >= requested_quantity
            shortfall = max(0, requested_quantity - current_stock)
            
            return Response({
                'available': available,
                'current_stock': current_stock,
                'requested_quantity': requested_quantity,
                'shortfall': shortfall,
                'product_id': int(product_id),
                'zone_id': int(zone_id),
                'product_name': stock.product.name if stock.product else None,
                'zone_name': stock.zone.name if stock.zone else None,
            })
        except Stock.DoesNotExist:
            return Response({
                'available': False,
                'current_stock': 0,
                'requested_quantity': requested_quantity,
                'shortfall': requested_quantity,
                'product_id': int(product_id),
                'zone_id': int(zone_id),
                'error': 'No stock record found for this product in this zone',
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StockSupplyViewSet(viewsets.ModelViewSet):
    """API endpoint for stock supplies"""
    queryset = StockSupply.objects.all().order_by('-date')
    serializer_class = StockSupplySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a stock supply - mark as completed"""
        stock_supply = self.get_object()
        
        if stock_supply.status == 'completed':
            return Response(
                {"error": "Cette livraison est déjà confirmée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        stock_supply.status = 'completed'
        stock_supply.save()
        
        # Return updated data
        serializer = self.get_serializer(stock_supply)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def outstanding_by_supplier(self, request):
        """Get outstanding supplies by supplier"""
        
        
        # Get all pending or partial supplies
        supplies = self.queryset.filter(
            Q(payment_status='unpaid') | Q(payment_status='partially_paid')
        )
        
        # Group by supplier and sum amounts
        result = []
        suppliers = Supplier.objects.all()
        
        for supplier in suppliers:
            supplier_supplies = supplies.filter(supplier=supplier)
            if supplier_supplies.exists():
                total = sum([s.total_amount for s in supplier_supplies])
                paid = sum([s.paid_amount for s in supplier_supplies])
                outstanding = total - paid
                
                if outstanding > 0:
                    result.append({
                        'supplier_id': supplier.id,
                        'supplier_name': supplier.name,
                        'total_amount': total,
                        'paid_amount': paid,
                        'outstanding_amount': outstanding,
                        'supply_count': supplier_supplies.count()
                    })
        
        # Sort by outstanding amount descending
        result.sort(key=lambda x: x['outstanding_amount'], reverse=True)
        return Response(result)

    @action(detail=True, methods=['post'])
    def pay_from_account(self, request, pk=None):
        """Process payment for a supply from company account to supplier account"""
        supply = self.get_object()
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', f'Payment for supply {supply.reference}')
        company_account_id = request.data.get('company_account')
        
        if amount <= 0:
            return Response(
                {'error': 'Payment amount must be greater than 0'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not company_account_id:
            return Response(
                {'error': 'company_account parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Generate reference number
                payment_count = SupplierCashPayment.objects.filter(
                    date=timezone.now().date()
                ).count()
                reference = f"PAYSUPP-{timezone.now().strftime('%Y%m%d')}-{payment_count + 1:04d}"
                
                # Get the supplier's account
                try:
                    supplier_account = Account.objects.get(account_type='supplier', supplier=supply.supplier)
                except Account.DoesNotExist:
                    return Response(
                        {'error': 'No account found for this supplier'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get the company account
                try:
                    company_account = Account.objects.get(id=company_account_id)
                except Account.DoesNotExist:
                    return Response(
                        {'error': 'Company account not found'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Note: We allow payments even with insufficient balance
                # This will result in a negative balance for the company account
                
                # Get last statement for supplier account
                last_supplier_statement = AccountStatement.objects.filter(
                    account=supplier_account
                ).order_by('-date', '-id').first()
                previous_supplier_balance = Decimal(str(last_supplier_statement.balance)) if last_supplier_statement else Decimal('0.00')
                
                # Get last statement for company account
                last_company_statement = AccountStatement.objects.filter(
                    account=company_account
                ).order_by('-date', '-id').first()
                previous_company_balance = Decimal(str(last_company_statement.balance)) if last_company_statement else Decimal('0.00')
                
                # Create SupplierCashPayment (payment record)
                payment = SupplierCashPayment.objects.create(
                    reference=reference,
                    account=company_account,
                    supply=supply,
                    supplier=supply.supplier,
                    date=timezone.now().date(),
                    amount=amount,
                    allocated_amount=amount,
                    description=description,
                    created_by=request.user
                )
                
                # Debit supplier account (reduce what we owe)
                new_supplier_balance = previous_supplier_balance - amount
                AccountStatement.objects.create(
                    account=supplier_account,
                    date=timezone.now().date(),
                    transaction_type='supply',
                    reference=reference,
                    description=f"Paiement approvisionnement {supply.reference} - {supply.supplier.name}",
                    credit=0,
                    debit=amount,
                    balance=new_supplier_balance,
                )
                supplier_account.current_balance = new_supplier_balance
                supplier_account.save(update_fields=['current_balance'])
                
                # Debit company account (money going out)
                new_company_balance = previous_company_balance - amount
                AccountStatement.objects.create(
                    account=company_account,
                    date=timezone.now().date(),
                    transaction_type='supply',
                    reference=reference,
                    description=f"Paiement fournisseur {supply.supplier.name} pour approvisionnement {supply.reference}",
                    credit=0,
                    debit=amount,
                    balance=new_company_balance,
                )
                company_account.current_balance = new_company_balance
                company_account.save(update_fields=['current_balance'])
                
                # Update supply payment status and amounts
                supply.refresh_from_db()
                paid_amount = SupplierCashPayment.objects.filter(supply=supply).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                
                supply.paid_amount = paid_amount
                supply.remaining_amount = supply.total_amount - paid_amount
                
                if paid_amount >= supply.total_amount:
                    supply.payment_status = 'paid'
                elif paid_amount > 0:
                    supply.payment_status = 'partially_paid'
                else:
                    supply.payment_status = 'unpaid'
                
                supply.save()
                
                # Return the updated supplier and company balances
                return Response({
                    'success': True,
                    'message': 'Payment processed successfully',
                    'payment': {
                        'id': payment.id,
                        'reference': payment.reference,
                        'amount': str(payment.amount),
                        'date': payment.date.isoformat()
                    },
                    'supply': {
                        'id': supply.id,
                        'reference': supply.reference,
                        'payment_status': supply.payment_status,
                        'workflow_state': supply.status,
                        'total_amount': str(supply.total_amount),
                        'paid_amount': str(supply.paid_amount),
                        'remaining_amount': str(supply.remaining_amount)
                    },
                    'supplier_balance': float(supplier_account.current_balance),
                    'company_balance': float(company_account.current_balance)
                })
        except Exception as e:
            return Response(
                {'error': f'Error processing payment: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class StockCardViewSet(viewsets.ModelViewSet):
    """API endpoint for stock cards"""
    queryset = StockCard.objects.all().order_by('-date')
    serializer_class = StockCardSerializer
    permission_classes = [IsAuthenticated]


class StockTransferViewSet(viewsets.ModelViewSet):
    """API endpoint for stock transfers between zones"""
    queryset = StockTransfer.objects.all().order_by('-date')
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InventoryViewSet(viewsets.ModelViewSet):
    """API endpoint for physical inventories"""
    queryset = Inventory.objects.prefetch_related('items__product').all().order_by('-date')
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not serializer.validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            with transaction.atomic():
                count = Inventory.objects.filter(reference__startswith=f'INV-{datestr}').count()
                reference = f'INV-{datestr}-{count+1:04d}'
            serializer.validated_data['reference'] = reference
        
        serializer.save(created_by=self.request.user)


class StockReturnViewSet(viewsets.ModelViewSet):
    """API endpoint for stock returns"""
    queryset = StockReturn.objects.prefetch_related('items__product').all().order_by('-date')
    serializer_class = StockReturnSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
