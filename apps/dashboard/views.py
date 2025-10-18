"""
Dashboard Views
Aggregated read-only views for dashboard display
Consolidates data from multiple domain apps
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, F, Q, Value, DecimalField, Max
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Import models from different domain apps
from apps.inventory.models import Stock, Product
from apps.inventory.serializers import StockSerializer
from apps.sales.models import Sale, SaleItem
from apps.sales.serializers import SaleSerializer
from apps.partners.models import Client, Supplier
from apps.treasury.models import Account


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get overall dashboard statistics
    Endpoint: /api/dashboard/stats/
    
    Query Parameters:
    - period: 'day', 'week', 'month', 'year' (default: 'year')
    - start_date: Custom start date (YYYY-MM-DD)
    - end_date: Custom end date (YYYY-MM-DD)
    """
    period = request.query_params.get('period', 'year')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Calculate date range
    today = datetime.now().date()
    if period == 'custom' and start_date and end_date:
        date_from = datetime.strptime(start_date, '%Y-%m-%d').date()
        date_to = datetime.strptime(end_date, '%Y-%m-%d').date()
    elif period == 'day':
        date_from = today
        date_to = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
        date_to = today
    elif period == 'month':
        date_from = today - timedelta(days=30)
        date_to = today
    else:  # year
        date_from = today - timedelta(days=365)
        date_to = today
    
    # Get sales statistics
    sales_queryset = Sale.objects.filter(date__range=[date_from, date_to])
    total_sales = sales_queryset.aggregate(
        total=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField()))
    )['total']
    
    # Get counts
    total_clients = Client.objects.filter(is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    
    return Response({
        'total_sales': float(total_sales),
        'total_clients': total_clients,
        'total_products': total_products,
        'total_suppliers': total_suppliers,
        'period': period,
        'date_from': str(date_from),
        'date_to': str(date_to),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_stats(request):
    """
    Get inventory statistics for dashboard
    Endpoint: /api/dashboard/inventory/
    
    Query Parameters:
    - period: 'day', 'week', 'month', 'year' (default: 'year')
    """
    period = request.query_params.get('period', 'year')
    
    # Get low stock count
    low_stock_count = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0
    ).count()
    
    # Get total stock count
    total_stock = Stock.objects.count()
    
    # Calculate total inventory value
    inventory_value = Stock.objects.aggregate(
        total=Coalesce(
            Sum(F('quantity') * F('product__selling_price')),
            Value(0, output_field=DecimalField())
        )
    )['total']
    
    # Get category breakdown
    category_data = Stock.objects.values(
        category_name=F('product__category__name')
    ).annotate(
        value=Sum(F('quantity') * F('product__selling_price'))
    ).filter(value__gt=0).order_by('-value')[:10]
    
    # Get zone breakdown
    zone_data = Stock.objects.values(
        zone_name=F('zone__name')
    ).annotate(
        value=Sum(F('quantity') * F('product__selling_price'))
    ).filter(value__gt=0).order_by('-value')
    
    return Response({
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
        'inventory_value': float(inventory_value),
        'total_value': float(inventory_value),  # Alias for compatibility
        'category_data': [
            {'category': item['category_name'] or 'Sans catégorie', 'value': float(item['value'])}
            for item in category_data
        ],
        'zone_data': [
            {'zone': item['zone_name'] or 'Sans zone', 'value': float(item['value'])}
            for item in zone_data
        ],
        'period': period,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_products(request):
    """
    Get products with low stock levels for dashboard display
    Endpoint: /api/dashboard/low-stock/
    """
    low_stock = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0
    ).select_related('product', 'product__category', 'zone', 'product__unit').order_by('product__name')
    
    # Format response with detailed information
    data = []
    for stock in low_stock:
        data.append({
            'id': stock.id,
            'product_id': stock.product.id,
            'name': stock.product.name,
            'category': stock.product.category.name if stock.product.category else 'Sans catégorie',
            'quantity': stock.quantity,
            'current_stock': stock.quantity,
            'threshold': stock.product.min_stock_level,
            'min_stock_level': stock.product.min_stock_level,
            'zone': stock.zone.name if stock.zone else 'Sans zone',
            'unit': stock.product.unit.symbol if stock.product.unit else '',
            'unit_symbol': stock.product.unit.symbol if stock.product.unit else '',
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_sales(request):
    """
    Get recent sales for dashboard display
    Endpoint: /api/dashboard/recent-sales/
    
    Query Parameters:
    - limit: Number of sales to return (default: 10)
    """
    limit = int(request.query_params.get('limit', 10))
    
    # Get recent sales
    sales = Sale.objects.select_related(
        'client', 'zone'
    ).order_by('-date', '-id')[:limit]
    
    serializer = SaleSerializer(sales, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_products(request):
    """
    Get top selling products
    Endpoint: /api/dashboard/top-products/
    
    Query Parameters:
    - period: 'day', 'week', 'month', 'year' (default: 'month')
    - limit: Number of products to return (default: 10)
    """
    period = request.query_params.get('period', 'month')
    limit = int(request.query_params.get('limit', 10))
    
    # Calculate date range
    today = datetime.now().date()
    if period == 'day':
        date_from = today
    elif period == 'week':
        date_from = today - timedelta(days=7)
    elif period == 'month':
        date_from = today - timedelta(days=30)
    else:  # year
        date_from = today - timedelta(days=365)
    
    top_products = SaleItem.objects.filter(
        sale__date__gte=date_from
    ).values(
        'product__id', 'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-revenue')[:limit]
    
    data = [
        {
            'id': item['product__id'],
            'name': item['product__name'],
            'quantity': float(item['quantity']),
            'revenue': float(item['revenue']),
        }
        for item in top_products
    ]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_trend(request):
    """
    Get revenue trend over time
    Endpoint: /api/dashboard/revenue-trend/
    
    Query Parameters:
    - period: 'week', 'month', 'year' (default: 'month')
    """
    period = request.query_params.get('period', 'month')
    
    # Calculate date range
    today = datetime.now().date()
    if period == 'week':
        date_from = today - timedelta(days=7)
        days = 7
    elif period == 'month':
        date_from = today - timedelta(days=30)
        days = 30
    else:  # year
        date_from = today - timedelta(days=365)
        days = 365
    
    # Get daily sales
    daily_sales = Sale.objects.filter(
        date__range=[date_from, today]
    ).values('date').annotate(
        amount=Sum('total_amount')
    ).order_by('date')
    
    # Create a complete dataset with all dates
    data = []
    for i in range(days + 1):
        current_date = date_from + timedelta(days=i)
        matching_sale = next(
            (item for item in daily_sales if item['date'] == current_date),
            None
        )
        data.append({
            'date': str(current_date),
            'amount': float(matching_sale['amount']) if matching_sale else 0,
        })
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_activity(request):
    """
    Get recent client activity
    Endpoint: /api/dashboard/client-activity/
    
    Query Parameters:
    - limit: Number of clients to return (default: 10)
    """
    limit = int(request.query_params.get('limit', 10))
    
    # Get clients with recent sales
    clients_with_sales = Sale.objects.values(
        'client__id', 'client__name'
    ).annotate(
        last_sale_date=Max('date'),
        total_amount=Sum('total_amount'),
        sale_count=Count('id')
    ).order_by('-last_sale_date')[:limit]
    
    data = [
        {
            'id': item['client__id'],
            'name': item['client__name'],
            'last_sale_date': str(item['last_sale_date']),
            'total_amount': float(item['total_amount']),
            'sale_count': item['sale_count'],
        }
        for item in clients_with_sales
    ]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_payments(request):
    """
    Get summary of pending payments
    Endpoint: /api/dashboard/pending-payments/
    """
    # Get pending sales
    pending_sales = Sale.objects.filter(
        payment_status__in=['pending', 'partial']
    ).aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField())),
        paid_amount=Coalesce(Sum('paid_amount'), Value(0, output_field=DecimalField()))
    )
    
    # Calculate outstanding amount
    outstanding_amount = pending_sales['total_amount'] - pending_sales['paid_amount']
    
    # Get pending supplies
    from apps.inventory.models import StockSupply
    pending_supplies = StockSupply.objects.filter(
        payment_status__in=['pending', 'partial']
    ).aggregate(
        count=Count('id'),
        total_amount=Coalesce(Sum('total_amount'), Value(0, output_field=DecimalField())),
        paid_amount=Coalesce(Sum('paid_amount'), Value(0, output_field=DecimalField()))
    )
    
    # Calculate outstanding supply amount
    outstanding_supply_amount = pending_supplies['total_amount'] - pending_supplies['paid_amount']
    
    return Response({
        'sales': {
            'count': pending_sales['count'],
            'total_amount': float(pending_sales['total_amount']),
            'paid_amount': float(pending_sales['paid_amount']),
            'outstanding_amount': float(outstanding_amount),
        },
        'supplies': {
            'count': pending_supplies['count'],
            'total_amount': float(pending_supplies['total_amount']),
            'paid_amount': float(pending_supplies['paid_amount']),
            'outstanding_amount': float(outstanding_supply_amount),
        },
        'total_outstanding': float(outstanding_amount + outstanding_supply_amount),
    })
