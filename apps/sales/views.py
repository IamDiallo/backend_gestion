from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, date

from .models import (
    Sale, SaleItem, DeliveryNote, Invoice, Quote, QuoteItem,
    SaleCharge, ChargeType
)
from .serializers import (
    SaleSerializer, SaleItemSerializer, DeliveryNoteSerializer,
    InvoiceSerializer, QuoteSerializer, QuoteItemSerializer,
    SaleChargeSerializer, ChargeTypeSerializer
)
from apps.treasury.models import Account, AccountStatement, CashReceipt
from apps.core.models import Zone
from apps.inventory.models import Stock


class SaleViewSet(viewsets.ModelViewSet):
    """API endpoint for sales"""
    queryset = Sale.objects.all().order_by('-date')
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def pay_from_account(self, request, pk=None):
        """Process payment for a sale from client account and credit company account"""
        sale = self.get_object()
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', f'Payment for sale {sale.reference}')
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
                payment_count = CashReceipt.objects.filter(
                    date=timezone.now().date()
                ).count()
                reference = f"PAY-{timezone.now().strftime('%Y%m%d')}-{payment_count + 1:04d}"
                
                # Get the client's account
                client_account = Account.objects.get(account_type='client', client=sale.client)
                if not client_account:
                    return Response(
                        {'error': 'No account found for this client'}, 
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
                
                # Get last statement for client account
                last_client_statement = AccountStatement.objects.filter(
                    account=client_account
                ).order_by('-date', '-id').first()
                previous_client_balance = Decimal(str(last_client_statement.balance)) if last_client_statement else Decimal('0.00')
                
                # Get last statement for company account
                last_company_statement = AccountStatement.objects.filter(
                    account=company_account
                ).order_by('-date', '-id').first()
                previous_company_balance = Decimal(str(last_company_statement.balance)) if last_company_statement else Decimal('0.00')
                
                # Create CashReceipt (payment record)
                payment = CashReceipt.objects.create(
                    reference=reference,
                    account=company_account,
                    sale=sale,
                    client=sale.client,
                    date=timezone.now().date(),
                    amount=amount,
                    allocated_amount=amount,
                    description=description,
                    created_by=request.user
                )
                
                # Debit client account
                new_client_balance = previous_client_balance - amount
                AccountStatement.objects.create(
                    account=client_account,
                    date=timezone.now().date(),
                    transaction_type='sale',
                    reference=reference,
                    description=f"Paiement vente {sale.reference} - {sale.client.name}",
                    credit=0,
                    debit=amount,
                    balance=new_client_balance,
                )
                client_account.current_balance = new_client_balance
                client_account.save(update_fields=['current_balance'])
                
                # Credit company account
                new_company_balance = previous_company_balance + amount
                AccountStatement.objects.create(
                    account=company_account,
                    date=timezone.now().date(),
                    transaction_type='sale',
                    reference=reference,
                    description=f"Paiement reçu de {sale.client.name} pour vente {sale.reference}",
                    credit=amount,
                    debit=0,
                    balance=new_company_balance,
                )
                company_account.current_balance = new_company_balance
                company_account.save(update_fields=['current_balance'])
                
                # Update sale payment status and amounts
                sale.refresh_from_db()
                paid_amount = CashReceipt.objects.filter(sale=sale).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                
                sale.paid_amount = paid_amount
                sale.remaining_amount = sale.total_amount - paid_amount
                
                if paid_amount >= sale.total_amount:
                    sale.payment_status = 'paid'
                elif paid_amount > 0:
                    sale.payment_status = 'partially_paid'
                else:
                    sale.payment_status = 'unpaid'
                
                sale.save()
                
                # Return the updated client and company balances
                return Response({
                    'success': True,
                    'message': 'Payment processed successfully',
                    'payment': {
                        'id': payment.id,
                        'reference': payment.reference,
                        'amount': str(payment.amount),
                        'date': payment.date.isoformat()
                    },
                    'sale': {
                        'id': sale.id,
                        'reference': sale.reference,
                        'payment_status': sale.payment_status,
                        'workflow_state': sale.status,
                        'total_amount': str(sale.total_amount),
                        'paid_amount': str(sale.paid_amount),
                        'remaining_amount': str(sale.remaining_amount)
                    },
                    'client_balance': float(client_account.current_balance),
                    'company_balance': float(company_account.current_balance),
                    'is_credit_payment': client_account.current_balance < 0
                })
                
        except Exception as e:
            return Response(
                {'error': f'Error processing payment: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def outstanding_by_client(self, request):
        """Get outstanding sales for a specific client"""
        client_id = request.query_params.get('client_id')
        
        if not client_id:
            return Response(
                {'error': 'client_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get sales with remaining amount > 0 for this client
            outstanding_sales = Sale.objects.filter(
                client_id=client_id,
                remaining_amount__gt=0
            ).select_related('client', 'zone').order_by('-date')
            
            serializer = self.get_serializer(outstanding_sales, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Error fetching outstanding sales: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def recalculate_payment_amounts(self, request):
        """Recalculate paid amounts for all sales based on cash receipts"""
        try:
            sales_updated = 0
            
            for sale in Sale.objects.all():
                # Calculate total paid amount from cash receipts
                paid_amount = CashReceipt.objects.filter(sale=sale).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                
                # Update sale amounts
                old_paid_amount = sale.paid_amount
                sale.paid_amount = paid_amount
                sale.remaining_amount = sale.total_amount - paid_amount
                
                # Update payment status
                if paid_amount >= sale.total_amount:
                    sale.payment_status = 'paid'
                elif paid_amount > 0:
                    sale.payment_status = 'partially_paid'
                else:
                    sale.payment_status = 'unpaid'
                
                # Only save if there's a change
                if old_paid_amount != paid_amount:
                    sale.save()
                    sales_updated += 1
            
            return Response({
                'success': True,
                'message': f'Payment amounts recalculated for {sales_updated} sales',
                'sales_updated': sales_updated
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error recalculating payment amounts: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeliveryNoteViewSet(viewsets.ModelViewSet):
    """API endpoint for delivery notes"""
    queryset = DeliveryNote.objects.all().order_by('-date')
    serializer_class = DeliveryNoteSerializer
    permission_classes = [IsAuthenticated]


class ChargeTypeViewSet(viewsets.ModelViewSet):
    """API endpoint for charge types"""
    queryset = ChargeType.objects.all().order_by('name')
    serializer_class = ChargeTypeSerializer
    permission_classes = [IsAuthenticated]


class SaleChargeViewSet(viewsets.ModelViewSet):
    """API endpoint for sale charges"""
    queryset = SaleCharge.objects.all()
    serializer_class = SaleChargeSerializer
    permission_classes = [IsAuthenticated]


class InvoiceViewSet(viewsets.ModelViewSet):
    """API endpoint for invoices"""
    queryset = Invoice.objects.all().order_by('-date')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]


class QuoteViewSet(viewsets.ModelViewSet):
    """API endpoint for quotes"""
    queryset = Quote.objects.all().order_by('-date')
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Let the model's save method handle reference generation
        serializer.save()

    @action(detail=True, methods=['post'])
    def convert_to_sale(self, request, pk=None):
        """Convert quote to sale"""
        quote = self.get_object()
        
        # Check if the quote has already been converted
        if quote.is_converted:
            return Response(
                {"error": "Ce devis a déjà été converti en vente"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the zone instance from the provided zone ID
        zone_id = request.data.get('zone')
        if not zone_id:
            return Response(
                {"error": "La zone est requise pour convertir le devis en vente"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zone = Zone.objects.get(id=zone_id)
        except Zone.DoesNotExist:
            return Response(
                {"error": "ID de zone invalide fourni"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a new sale with data from the quote
        sale = Sale.objects.create(
            reference=f"VNT-{quote.reference}",
            client=quote.client,
            zone=zone,
            date=timezone.now().date(),
            status='payment_pending',
            subtotal=quote.subtotal,
            discount_amount=0,
            tax_amount=quote.tax_amount,
            total_amount=quote.total_amount,
            notes=f"Créé à partir du devis {quote.reference}",
            created_by=request.user
        )
        
        # Copy quote items to sale items
        for quote_item in quote.items.all():
            SaleItem.objects.create(
                sale=sale,
                product=quote_item.product,
                quantity=quote_item.quantity,
                unit_price=quote_item.unit_price,
                discount_percentage=quote_item.discount_percentage,
                total_price=quote_item.total_price
            )
        
        # Mark the quote as converted
        quote.is_converted = True
        quote.save()
        
        # Return the sale data
        sale_serializer = SaleSerializer(sale)
        return Response(sale_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_sales(request):
    """Get sales report data"""
    from apps.inventory.models import ProductCategory
    
    period = request.query_params.get('period', 'year')
    start_date_param = request.query_params.get('start_date')
    end_date_param = request.query_params.get('end_date')
    
    today = datetime.now().date()
    if period == 'month':
        start_date = datetime(today.year, today.month, 1).date()
        end_date = today
    elif period == 'quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = datetime(today.year, 3 * current_quarter - 2, 1).date()
        if current_quarter < 4:
            next_quarter_start = datetime(today.year, 3 * (current_quarter + 1) - 2, 1).date()
            end_date = next_quarter_start - timedelta(days=1)
        else:
            end_date = datetime(today.year, 12, 31).date()
    elif period == 'semester':
        current_semester = 1 if today.month <= 6 else 2
        if current_semester == 1:
            start_date = datetime(today.year, 1, 1).date()
            end_date = datetime(today.year, 6, 30).date()
        else:
            start_date = datetime(today.year, 7, 1).date()
            end_date = datetime(today.year, 12, 31).date()
    elif period == 'year':
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    elif period == 'custom':
        try:
            if not start_date_param or not end_date_param:
                start_date = today - timedelta(days=30)
                end_date = today
            else:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    
    if not isinstance(start_date, date):
        start_date = today - timedelta(days=30)
    if not isinstance(end_date, date):
        end_date = today
    
    monthly_data = []
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    
    # Get the year to use for monthly data
    year = start_date.year if isinstance(start_date, date) else datetime.now().year
    
    for month in range(1, 13):
        month_sales = Sale.objects.filter(
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_data.append({
            'month': months[month-1],
            'amount': float(month_sales)
        })
    
    category_data = []
    categories = ProductCategory.objects.all()
    
    for category in categories:
        category_sales = SaleItem.objects.filter(
            sale__date__gte=start_date,
            sale__date__lte=end_date,
            product__category=category
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        if category_sales > 0:
            category_data.append({
                'category': category.name,
                'amount': float(category_sales)
            })
    
    top_products = []
    sales_items = SaleItem.objects.filter(
        sale__date__gte=start_date,
        sale__date__lte=end_date
    ).select_related('product').values(
        'product__id',
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:5]
    
    for item in sales_items:
        top_products.append({
            'name': item['product__name'],
            'quantity': float(item['total_quantity']),
            'revenue': float(item['total_revenue'])
        })
    
    return Response({
        'monthly_data': monthly_data,
        'category_data': category_data,
        'top_products': top_products
    })

