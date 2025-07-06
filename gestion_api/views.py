from django.shortcuts import render
from rest_framework import viewsets, status, views
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings  # Add missing import
from .models import (
    Product, Client, Supplier, Sale, SaleItem, UserProfile, ProductCategory,
    Production, ProductionMaterial, StockSupply, StockSupplyItem, StockTransfer,
    StockTransferItem, Inventory, InventoryItem, StockCard, DeliveryNote,UnitOfMeasure,
    DeliveryNoteItem, ChargeType, SaleCharge, ClientGroup, Employee, Zone, Invoice, Quote, QuoteItem,
    Currency, ExchangeRate, PaymentMethod, Account, PriceGroup, ExpenseCategory, Expense,
    ClientPayment, SupplierPayment, AccountTransfer, CashFlow, BankReconciliation, FinancialReport, Stock, CashReceipt, AccountStatement, AccountPayment
)
from .serializers import (
    ProductSerializer, ClientSerializer, SupplierSerializer, SaleSerializer, SaleItemSerializer, UserProfileSerializer, 
    PermissionSerializer, GroupSerializer, ZoneSerializer,
    CurrencySerializer, ExchangeRateSerializer, PaymentMethodSerializer,
    AccountSerializer, PriceGroupSerializer, ExpenseCategorySerializer,
    ExpenseSerializer, ClientPaymentSerializer, SupplierPaymentSerializer,
    AccountTransferSerializer, CashFlowSerializer, BankReconciliationSerializer,
    FinancialReportSerializer, ProductCategorySerializer, UnitOfMeasureSerializer,
    ProductionSerializer, ProductionMaterialSerializer, StockSupplySerializer, StockSupplyItemSerializer,
    StockTransferSerializer, StockTransferItemSerializer, InventorySerializer, InventoryItemSerializer
)
from rest_framework import serializers
from django.db.models import Sum, Count, Q, F # Add F expression
from django.db import transaction
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal

import json
import qrcode
from io import BytesIO
from django.http import HttpResponse
from rest_framework.decorators import action
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# Add these CORS decorators to your API views
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Add a decorator to handle OPTIONS requests properly for the dashboard_stats view

from django.http import HttpResponse
from decimal import Decimal  # Add this import

# Add this function to handle OPTIONS requests
def options_response(request):
    response = HttpResponse()
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Add the HasGroupPermission class that's missing
class HasGroupPermission(BasePermission):
    """
    Custom permission to check if user has the right permissions to manage groups
    """
    def has_permission(self, request, view):
        # Always allow GET requests for listing and viewing
        if request.method == 'GET':
            return True
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
            
        # Superusers can do everything
        if request.user.is_superuser:
            return True
            
        # If user has profile with admin role, allow all operations
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            return True
            
        # Check specific permissions based on action
        if view.action == 'create':
            return request.user.has_perm('auth.add_group')
        elif view.action in ['update', 'partial_update']:
            return request.user.has_perm('auth.change_group')
        elif view.action == 'destroy':
            return request.user.has_perm('auth.delete_group')
        
        # Default to False for other actions
        return False

# Dashboard API views
@api_view(['GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
@csrf_exempt  # Add CSRF exemption for API endpoints
def dashboard_stats(request):
    """
    Get dashboard statistics
    """
    # Handle OPTIONS request
    if request.method == 'OPTIONS':
        return options_response(request)
    
    # Get query parameters
    period = request.query_params.get('period', 'year')
    start_date_param = request.query_params.get('start_date')
    end_date_param = request.query_params.get('end_date')
    
    # Set default date range based on period
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
        # First semester: Jan-Jun, Second semester: Jul-Dec
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
                return Response(
                    {"error": "Both start_date and end_date are required for custom period"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Default to current year if unknown period
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    
    # Ensure start_date and end_date are always date objects
    if not isinstance(start_date, date):
        start_date = datetime(today.year, 1, 1).date()
    if not isinstance(end_date, date):
        end_date = datetime(today.year, 12, 31).date()
    
    # Apply date filters to sales
    sales_queryset = Sale.objects.filter(date__gte=start_date, date__lte=end_date)
    
    total_sales = sales_queryset.count()
    total_clients = Client.objects.count()
    total_products = Product.objects.count()
    total_suppliers = Supplier.objects.count()
    
    return Response({
        'total_sales': total_sales,
        'total_clients': total_clients,
        'total_products': total_products,
        'total_suppliers': total_suppliers
    })

@api_view(['GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def dashboard_recent_sales(request):
    """
    Get recent sales for dashboard
    """
    # Handle OPTIONS request
    if request.method == 'OPTIONS':
        return options_response(request)
    
    recent_sales = Sale.objects.all().order_by('-date')[:5]
    data = [
        {
            'id': sale.id,
            'reference': sale.reference,
            'client': sale.client.name,
            'date': sale.date,
            'total_amount': sale.total_amount
        }
        for sale in recent_sales
    ]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def dashboard_low_stock(request):
    """
    Get low stock items for dashboard
    """
    # Get products with stock below minimum level
    low_stock = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0  # Only consider products with a minimum set
    ).select_related('product', 'zone')
    
    data = [
        {
            'id': stock.product.id,
            'name': stock.product.name,
            'category': stock.product.category.name if stock.product.category else 'N/A',
            'quantity': stock.quantity,
            'threshold': stock.product.min_stock_level,
            'zone': stock.zone.name,
            'unit': stock.product.unit.symbol if stock.product.unit else '',
        }
        for stock in low_stock[:10]  # Limit to 10 items
    ]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def inventory_dashboard(request):
    """
    Get inventory statistics for dashboard
    """
    # Get query parameters
    period = request.query_params.get('period', 'year')
    start_date_param = request.query_params.get('start_date')
    end_date_param = request.query_params.get('end_date')
    
    # Set default date range based on period
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
        # First semester: Jan-Jun, Second semester: Jul-Dec
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
                # Default to last 30 days if custom dates not provided
                start_date = today - timedelta(days=30)
                end_date = today
            else:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Fall back to last 30 days if invalid dates
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        # Default to current year if unknown period
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    
    # Ensure start_date and end_date are always date objects
    if not isinstance(start_date, date):
        start_date = today - timedelta(days=30)
    if not isinstance(end_date, date):
        end_date = today
    
    # Get total inventory value (current stock)
    inventory_value = Stock.objects.annotate(
        value=F('quantity') * F('product__purchase_price')
    ).aggregate(total=Sum('value'))['total'] or 0
    
    # Get products with stock below minimum level
    low_stock_products = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0  # Only consider products with a minimum stock level set
    ).select_related('product', 'zone').order_by('quantity')[:10]
    
    low_stock_data = [
        {
            'id': stock.product.id,
            'name': stock.product.name,
            'zone': stock.zone.name,
            'quantity': stock.quantity,
            'min_level': stock.product.min_stock_level,
            'unit': stock.product.unit.symbol if stock.product.unit else '',
        }
        for stock in low_stock_products
    ]
    
    # Get stock value per product (top 20 by value)
    product_stock_values = Stock.objects.select_related('product', 'zone', 'product__unit').annotate(
        stock_value=F('quantity') * F('product__purchase_price')
    ).filter(
        quantity__gt=0  # Only products with stock
    ).order_by('-stock_value')[:20]
    
    product_stock_data = [
        {
            'product_id': stock.product.id,
            'product_name': stock.product.name,
            'zone_name': stock.zone.name,
            'quantity': stock.quantity,
            'unit_price': float(stock.product.purchase_price),
            'stock_value': float(stock.quantity * stock.product.purchase_price),
            'unit_symbol': stock.product.unit.symbol if stock.product.unit else '',
        }
        for stock in product_stock_values
    ]
    
    # Get inventory movement statistics with date filtering
    recent_movements = StockCard.objects.filter(date__gte=start_date, date__lte=end_date)
    
    inflow = recent_movements.aggregate(total=Sum('quantity_in'))['total'] or 0
    outflow = recent_movements.aggregate(total=Sum('quantity_out'))['total'] or 0
    
    # Get top product categories by inventory value
    category_values = Stock.objects.values(
        'product__category__name'
    ).annotate(
        value=Sum(F('quantity') * F('product__purchase_price'))
    ).order_by('-value')[:5]
    
    category_data = [
        {
            'category': item['product__category__name'] or 'Uncategorized',
            'value': item['value']
        }
        for item in category_values if item['value'] is not None
    ]
    
    # Get top zones by inventory value
    zone_values = Stock.objects.values(
        'zone__name'
    ).annotate(
        value=Sum(F('quantity') * F('product__purchase_price'))
    ).order_by('-value')[:5]
    
    zone_data = [
        {
            'zone': item['zone__name'],
            'value': item['value']
        }
        for item in zone_values if item['value'] is not None
    ]
    
    return Response({
        'inventory_value': inventory_value,
        'low_stock_products': low_stock_data,
        'product_stock_values': product_stock_data,
        'inflow': inflow,
        'outflow': outflow,
        'category_data': category_data,
        'zone_data': zone_data
    })

# Reports API views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def reports_sales(request):
    """
    Get sales report data
    """
    # Get query parameters
    period = request.query_params.get('period', 'year')
    start_date_param = request.query_params.get('start_date')
    end_date_param = request.query_params.get('end_date')
    
    # Set default date range based on period
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
        # First semester: Jan-Jun, Second semester: Jul-Dec
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
                return Response(
                    {"error": "Both start_date and end_date are required for custom period"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Default to current year if unknown period
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    
    # Ensure start_date and end_date are always date objects
    if not isinstance(start_date, date):
        start_date = datetime(today.year, 1, 1).date()
    if not isinstance(end_date, date):
        end_date = datetime(today.year, 12, 31).date()
    
    # Generate monthly sales data
    monthly_data = []
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    
    for month in range(1, 13):
        # Get sales for this month
        month_start = datetime(today.year, month, 1).date()
        if month < 12:
            month_end = datetime(today.year, month + 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(today.year, 12, 31).date()
        
        # Skip months outside the selected period
        if month_end < start_date or month_start > end_date:
            continue
        
        # Calculate total sales amount for the month
        month_sales = Sale.objects.filter(
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('total_amount'))
        
        monthly_data.append({
            'month': months[month - 1],
            'amount': month_sales['total'] or 0
        })
    
    # Get sales by category
    category_data = []
    categories = ProductCategory.objects.all()
    
    for category in categories:
        # Get products in this category
        products = Product.objects.filter(category=category)
        
        # Get sales items for these products
        sales_items = SaleItem.objects.filter(
            product__in=products,
            sale__date__gte=start_date,
            sale__date__lte=end_date
        )
        
        # Calculate total sales value
        total_value = sales_items.aggregate(total=Sum('total_price'))['total'] or 0
        
        if total_value > 0:
            category_data.append({
                'category': category.name,
                'amount': total_value
            })
    
    # Get top selling products
    top_products = []
    
    # Get sales items for the period
    sales_items = SaleItem.objects.filter(
        sale__date__gte=start_date,
        sale__date__lte=end_date
    ).values('product').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:5]
    
    for item in sales_items:
        product = Product.objects.get(id=item['product'])
        top_products.append({
            'id': product.id,
            'name': product.name,
            'quantity': item['total_quantity'],
            'revenue': item['total_revenue']
        })
    
    return Response({
        'monthly_data': monthly_data,
        'category_data': category_data,
        'top_products': top_products
    })

# User serializer and viewset
class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user profiles
    """
    queryset = UserProfile.objects.all().select_related('user', 'zone')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Add filtering by is_active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if not self.request.user.is_superuser:
            # Only allow users to see their own profile unless they're an admin
            profile = UserProfile.objects.filter(user=self.request.user).first()
            if profile and profile.role == 'admin':
                return queryset
            return queryset.filter(user=self.request.user)
        return queryset

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        user = self.get_object().user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Both old_password and new_password are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, 
                           status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'status': 'Mot de passe modifié avec succès'})
        
    @action(detail=True, methods=['get'])
    def check_permission(self, request, pk=None):
        profile = self.get_object()
        permission_code = request.query_params.get('permission_code')
        
        if not permission_code:
            return Response(
                {"error": "Permission code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        has_perm = profile.has_permission(permission_code)
        return Response({"has_permission": has_perm})

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for permissions (read-only)
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
            
    @action(detail=False, methods=['get'])
    def categorized(self, request):
        """
        Return permissions grouped by model/functionality
        """     
        all_permissions = Permission.objects.select_related('content_type').all()
        # Group permissions by content type
        categorized = {}
        for perm in all_permissions:
            app_model = f"{perm.content_type.app_label}.{perm.content_type.model}"
            if app_model not in categorized:
                categorized[app_model] = {
                    'name': perm.content_type.name.capitalize(),
                    'app': perm.content_type.app_label,
                    'model': perm.content_type.model,
                    'permissions': []
                }
            # Add permission with a more user-friendly name
            friendly_name = perm.name
            if friendly_name.startswith('Can '):
                friendly_name = friendly_name[4:]  # Remove "Can " prefix
            categorized[app_model]['permissions'].append({
                'id': perm.id,
                'codename': perm.codename,
                'name': friendly_name,
                'full_codename': f"{perm.content_type.app_label}.{perm.codename}"
            })
            
        # Convert to list for easier frontend processing
        result = list(categorized.values())
        # Sort by app and model name
        result.sort(key=lambda x: (x['app'], x['name']))
        return Response(result)

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user groups
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def create(self, request, *args, **kwargs):
        try:
            # Extract permissions from request data
            permissions_data = request.data.get('permissions', [])
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            group = serializer.save()
            # Extract permissions from request data
            # Add permissions to the group
            if permissions_data:
                # Convert from IDs to Permission objects if needed
                if isinstance(permissions_data[0], int):
                    permissions = Permission.objects.filter(id__in=permissions_data)
                else:
                    # Handle case where permissions are passed as codenames
                    permissions = Permission.objects.filter(codename__in=permissions_data)
                group.permissions.set(permissions)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
                
    def update(self, request, *args, **kwargs):
        try:
            # Extract permissions from request data
            permissions_data = request.data.get('permissions', [])
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            group = serializer.save()
            # Update permissions if provided
            if permissions_data:
                # Convert from IDs to Permission objects if needed
                if isinstance(permissions_data[0], int):
                    permissions = Permission.objects.filter(id__in=permissions_data)
                else:
                    # Handle case where permissions are passed as codenames
                    permissions = Permission.objects.filter(codename__in=permissions_data)
                group.permissions.set(permissions)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    @action(detail=True, methods=['post'])
    def add_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        
        if not permission_ids:
            return Response(
                {"error": "No permission IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        permissions = Permission.objects.filter(id__in=permission_ids)
        group.permissions.add(*permissions)
        return Response(
            {"status": "Permissions added to group successfully"}, 
            status=status.HTTP_200_OK
        )
        
    @action(detail=True, methods=['post'])
    def remove_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        
        if not permission_ids:
            return Response(
                {"error": "No permission IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        permissions = Permission.objects.filter(id__in=permission_ids)
        group.permissions.remove(*permissions)
        return Response(
            {"status": "Permissions removed from group successfully"}, 
            status=status.HTTP_200_OK
        )
        
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        group = self.get_object()
        # Only use Django's built-in user-group relationship
        users = User.objects.filter(groups=group)
        data = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': f"{user.first_name} {user.last_name}".strip()
            }
            for user in users
        ]
        return Response(data, status=status.HTTP_200_OK)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for products
    """
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        # Get category if provided to help generate the reference
        category_id = data.get('category')
        category = None
        
        if category_id:
            try:
                category = ProductCategory.objects.get(pk=category_id)
            except ProductCategory.DoesNotExist:
                pass
        
        # Generate reference if not provided
        if not data.get('reference'):
            # Create a temporary product instance to use the instance method
            temp_product = Product(category=category)
            data['reference'] = temp_product.generate_reference()
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'], url_path='qr-code')
    def qr_code(self, request, pk=None):
        """
        Generate a QR code for the product
        """
        product = self.get_object()
        qr_data = product.generate_qr_code_data()
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        # Create an image from the QR Code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code to a BytesIO buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Return the image as a HTTP response
        return HttpResponse(buffer, content_type="image/png")

# Zone serializer and viewset
class ZoneViewSet(viewsets.ModelViewSet):
    """
    API endpoint for zones
    """
    queryset = Zone.objects.all().order_by('name')
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

# Client serializer and viewset
class ClientViewSet(viewsets.ModelViewSet):
    """
    API endpoint for clients
    """
    queryset = Client.objects.all().order_by('name')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if 'account' in data and not data['account']:
            # If account field is provided but empty, remove it to use default
            data.pop('account') 
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        if Sale.objects.filter(client=client).exists():
            return Response(
                {"error": "Cannot delete client with associated sales. Deactivate instead."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

# Supplier serializer and viewset
class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint for suppliers
    """
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

# Sale serializer and viewset
class SaleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for sales
    """
    queryset = Sale.objects.prefetch_related('items__product').all().order_by('-date')  # Prefetch related items and products
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by client
        client_id = self.request.query_params.get('client', None)
        if client_id:
            queryset = queryset.filter(client=client_id)
        
        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            # Handle comma-separated payment statuses
            if ',' in payment_status:
                status_list = payment_status.split(',')
                queryset = queryset.filter(payment_status__in=status_list)
            else:
                queryset = queryset.filter(payment_status=payment_status)
        
        # Additional filters can be added here
        return queryset
    
    def perform_create(self, serializer):
        """
        When creating a sale, also record it in stock if status is confirmed or delivered
        """
        sale = serializer.save(created_by=self.request.user)
        
        # Update stock and record movements if sale is confirmed or delivered
        if sale.status in ['confirmed', 'delivered']:
            self._update_stock_for_sale(sale)
    
    def update(self, request, *args, **kwargs):
        """
        Override update to handle stock updates when sale status changes
        """
        instance = self.get_object()
        old_status = instance.status
          # Perform the update
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get the new status from request data if it exists
            new_status = request.data.get('status', instance.status)
            
            # Validate status transitions            # Ensure workflow_state is synchronized with status
            if 'status' in request.data:
                request.data['workflow_state'] = new_status
            
            # Serialize and save the updated sale
            updated_sale = serializer.save()
            
            # Update payment status and sale status based on payment amounts
            self._update_payment_status_from_amounts(updated_sale)
            
            new_status = updated_sale.status
            
            # If status changed to confirmed or delivered, update stock
            if old_status not in ['confirmed', 'delivered'] and new_status in ['confirmed', 'delivered']:
                self._update_stock_for_sale(updated_sale)
                
            # If status changed from confirmed/delivered to cancelled, we need to restore stock
            elif old_status in ['confirmed', 'delivered'] and new_status == 'cancelled':
                self._restore_stock_for_cancelled_sale(updated_sale, request.user)
                
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"Error updating sale: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _update_stock_for_sale(self, sale):
        """
        Update stock quantities and record stock card entries for a sale
        """
        with transaction.atomic():
            # Process each item in the sale
            for item in sale.items.all():
                # Get the corresponding stock record
                try:
                    stock = Stock.objects.select_for_update().get(
                        product=item.product, 
                        zone=sale.zone
                    )
                    
                    # Check if there's enough stock
                    if stock.quantity < item.quantity:
                        raise serializers.ValidationError(
                            f"Insufficient stock for product {item.product.name}. "
                            f"Available: {stock.quantity}, Required: {item.quantity}"
                        )
                    
                    # Reduce the stock quantity
                    stock.quantity -= item.quantity
                    stock.save()
                    
                    # Record the stock movement
                    StockCard.objects.create(
                        product=item.product,
                        zone=sale.zone,
                        date=sale.date,
                        transaction_type='sale',
                        reference=sale.reference,
                        quantity_in=0,
                        quantity_out=item.quantity,
                        unit_price=item.unit_price,
                        balance=stock.quantity,
                        notes=f"Sale: {sale.reference}"
                    )
                    
                except Stock.DoesNotExist:
                    # If stock record doesn't exist, we can't fulfill this order
                    raise serializers.ValidationError(
                        f"No stock record found for product {item.product.name} in zone {sale.zone.name}"
                    )
    
    def _restore_stock_for_cancelled_sale(self, sale, user=None):
        """
        Restore stock quantities and handle payment refunds when a sale is cancelled
        """
        with transaction.atomic():
            # 1. Restore stock quantities
            for item in sale.items.all():
                # Get or create the stock record
                stock, created = Stock.objects.select_for_update().get_or_create(
                    product=item.product,
                    zone=sale.zone,
                    defaults={'quantity': 0}
                )
                
                # Increase the stock quantity
                stock.quantity += item.quantity
                stock.save()
                
                # Record the stock movement as a return
                StockCard.objects.create(
                    product=item.product,
                    zone=sale.zone,
                    date=timezone.now().date(),
                    transaction_type='return',
                    reference=f"CANCEL-{sale.reference}",
                    quantity_in=item.quantity,
                    quantity_out=0,
                    unit_price=item.unit_price,
                    balance=stock.quantity,
                    notes=f"Cancelled sale: {sale.reference}"
                )
            
            # 2. Handle payment refunds if any payments were made
            if sale.paid_amount and sale.paid_amount > 0:
                client = sale.client
                
                # Ensure client has an account for refunds
                if not hasattr(client, 'account') or not client.account:
                    # Create a client account if it doesn't exist
                    from .models import Account, Currency
                    default_currency = Currency.objects.filter(is_base=True).first()
                    if not default_currency:
                        default_currency = Currency.objects.first()
                    
                    client_account = Account.objects.create(
                        name=f"Compte {client.name}",
                        account_type='client',
                        currency=default_currency,
                        initial_balance=0,
                        current_balance=0
                    )
                    client.account = client_account
                    client.save()
                
                # Credit the client account with the paid amount (refund)
                refund_amount = sale.paid_amount
                client.account.current_balance += refund_amount
                client.account.save()
                
                # Create account statement entry for the refund
                from .models import AccountStatement
                AccountStatement.objects.create(
                    account=client.account,
                    date=timezone.now().date(),
                    transaction_type='refund',
                    reference=f"CANCEL-REFUND-{sale.reference}",
                    description=f"Remboursement pour annulation de vente {sale.reference}",
                    credit=refund_amount,
                    debit=0,
                    balance=client.account.current_balance
                )
                
                # Create cash flow record for the refund
                CashFlow.objects.create(
                    reference=f"CANCEL-REFUND-{sale.reference}",
                    date=timezone.now().date(),
                    flow_type='refund',
                    amount=refund_amount,
                    description=f"Remboursement pour annulation de vente {sale.reference}",
                    account=client.account,
                    related_document_type='sale',
                    related_document_id=sale.id,
                    created_by=user
                )

    def _update_payment_status_from_amounts(self, sale):
        """
        Update payment status and sale status based on payment amounts
        """
        # Calculate remaining amount
        remaining_amount = sale.total_amount - (sale.paid_amount or 0)
        
        # Update payment status based on amounts
        if sale.paid_amount is None or sale.paid_amount == 0:
            payment_status = 'unpaid'
        elif remaining_amount <= 0:
            payment_status = 'paid'
        else:
            payment_status = 'partially_paid'
        
        # Update payment status if it has changed
        if sale.payment_status != payment_status:
            sale.payment_status = payment_status
            
            # Also update sale status to reflect payment status
            # Only update if current status allows it (don't override manual status changes)
            if payment_status == 'partially_paid' and sale.status in ['pending', 'confirmed', 'payment_pending']:
                sale.status = 'partially_paid'
                sale.workflow_state = 'partially_paid'
            elif payment_status == 'paid' and sale.status in ['pending', 'confirmed', 'payment_pending', 'partially_paid']:
                sale.status = 'paid'
                sale.workflow_state = 'paid'
            
            sale.save()
    
    # ...existing code...
    
    @action(detail=True, methods=['post'])
    def pay_from_account(self, request, pk=None):
        """
        Pay a sale using the client's account balance
        """
        sale = self.get_object()
        client = sale.client
        amount = Decimal(str(request.data.get('amount')))
        description = request.data.get('description', f"Paiement de vente {sale.reference} depuis compte client")
        
        # Validate client has an account
        if not client.account:
            return Response({"error": "Client has no associated account"}, status=400)
            
        # We're allowing credit payments (negative balance), but we'll include
        # a flag in the response to indicate if this is a credit payment
        is_credit_payment = client.account.current_balance < amount
            
        # Process payment using transaction to ensure atomicity
        with transaction.atomic():
            # Generate reference
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            count = AccountPayment.objects.filter(reference__startswith=f'ACCT-{datestr}').count()
            reference = f'ACCT-{datestr}-{count+1:04d}'
            
            # 1. Create account payment record
            account_payment = AccountPayment.objects.create(
                client=client,
                sale=sale,
                amount=amount,
                date=timezone.now().date(),
                reference=reference,
                description=description,
                created_by=request.user
            )
            
            # 2. Update client account balance
            client.account.current_balance -= amount
            client.account.save()
            
            # 3. Create account statement entry
            AccountStatement.objects.create(
                account=client.account,
                date=timezone.now().date(),
                transaction_type='sale',
                reference=reference,
                description=description,                debit=amount,
                credit=0,
                balance=client.account.current_balance
            )
            # 4. Update sale payment status
            sale_total = sale.total_amount
            sale_payments = CashReceipt.objects.filter(sale=sale).aggregate(Sum('amount'))['amount__sum'] or 0
            sale_account_payments = AccountPayment.objects.filter(sale=sale).aggregate(Sum('amount'))['amount__sum'] or 0
            total_paid = sale_payments + sale_account_payments
            remaining_amount = max(0, sale_total - total_paid)
            
            print(f"DEBUG: Sale ID: {sale.id}, Total: {sale_total}, Paid: {total_paid}, Remaining: {remaining_amount}")
            print(f"DEBUG: Before update - Payment status: {sale.payment_status}, Workflow state: {sale.workflow_state}, Status: {sale.status}")
            
            # Update the paid_amount and remaining_amount fields
            sale.paid_amount = total_paid
            sale.remaining_amount = remaining_amount
            
            if total_paid >= sale_total:
                sale.payment_status = 'paid'
                sale.workflow_state = 'paid'
                # If the sale is in payment_pending or confirmed status, automatically update to paid
                if sale.status in ['payment_pending', 'confirmed']:
                    sale.status = 'paid'
            elif total_paid > 0:
                sale.payment_status = 'partially_paid'
                sale.workflow_state = 'partially_paid'
                # Update status field for partially_paid
                if sale.status in ['payment_pending', 'draft']:
                    sale.status = 'partially_paid'
            
            print(f"DEBUG: After update - Payment status: {sale.payment_status}, Workflow state: {sale.workflow_state}, Status: {sale.status}")
            print(f"DEBUG: Paid amount: {sale.paid_amount}, Remaining amount: {sale.remaining_amount}")
            
            sale.save()
            
            # Verify the status was saved by re-fetching the sale
            sale_check = Sale.objects.get(pk=sale.id)
            print(f"DEBUG: After save - Payment status: {sale_check.payment_status}, Workflow state: {sale_check.workflow_state}, Status: {sale_check.status}")
            print(f"DEBUG: After save - Paid amount: {sale_check.paid_amount}, Remaining amount: {sale_check.remaining_amount}")
            
            # 5. Create CashFlow record for reporting
            CashFlow.objects.create(
                reference=reference,
                date=timezone.now().date(),
                flow_type='client_payment',
                amount=amount,
                description=description,
                account=client.account,
                related_document_type='sale',
                related_document_id=sale.id,
                created_by=request.user
            )
            
            return Response({
                "success": True,
                "message": f"Payment of {amount} processed successfully from client account",
                "payment": {
                    "id": account_payment.id,
                    "reference": account_payment.reference,
                    "amount": float(account_payment.amount),
                    "date": account_payment.date.strftime("%Y-%m-%d")
                },
                "sale": {
                    "id": sale.id,
                    "reference": sale.reference,
                    "payment_status": sale.payment_status,
                    "workflow_state": sale.workflow_state,
                    "status": sale.status,
                    "total_amount": float(sale.total_amount),
                    "paid_amount": float(total_paid),
                    "remaining_amount": float(remaining_amount)
                },
                "client_balance": float(client.account.current_balance),
                "is_credit_payment": is_credit_payment
            })
    
    def destroy(self, request, *args, **kwargs):
        """
        Safe deletion of sales - only allows deletion of 'pending' or 'cancelled' sales.
        For 'pending' sales: No additional actions needed (no stock or payments involved).
        For 'cancelled' sales: Stock and payment refunds were already handled during cancellation.
        """
        sale = self.get_object()
        
        # Check if sale can be safely deleted
        if sale.status not in ['pending', 'cancelled']:
            return Response(
                {
                    "error": "Sale deletion not allowed", 
                    "message": f"Sales with status '{sale.get_status_display()}' cannot be deleted. Only 'pending' or 'cancelled' sales can be deleted."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                deletion_summary = {
                    "sale_reference": sale.reference,
                    "client_name": sale.client.name,
                    "total_amount": float(sale.total_amount),
                    "status": sale.status,
                    "deleted_at": timezone.now().isoformat(),
                    "stock_restored": [],
                    "payment_refunded": 0,
                    "notes": []
                }
                
                if sale.status == 'pending':
                    # For pending sales, no stock or payment actions are needed
                    deletion_summary["notes"].append("No stock or payment actions required for pending sale")
                    
                elif sale.status == 'cancelled':
                    # For cancelled sales, stock and payments were already handled during cancellation
                    deletion_summary["notes"].append("Stock restoration and payment refunds were already processed during sale cancellation")
                    # Add information about what was already processed
                    deletion_summary["paid_amount"] = float(sale.paid_amount or 0)
                    if sale.paid_amount and sale.paid_amount > 0:
                        deletion_summary["notes"].append(f"Payment refund of {sale.paid_amount} was already processed during cancellation")
                
                # Delete related records first (due to foreign key constraints)
                # Delete cash receipts related to this sale
                from .models import CashReceipt, AccountPayment
                cash_receipts_count = CashReceipt.objects.filter(sale=sale).count()
                account_payments_count = AccountPayment.objects.filter(sale=sale).count()
                
                CashReceipt.objects.filter(sale=sale).delete()
                AccountPayment.objects.filter(sale=sale).delete()
                
                if cash_receipts_count > 0:
                    deletion_summary["notes"].append(f"Deleted {cash_receipts_count} cash receipt(s)")
                if account_payments_count > 0:
                    deletion_summary["notes"].append(f"Deleted {account_payments_count} account payment(s)")
                
                # Delete sale items
                items_count = sale.items.count()
                sale.items.all().delete()
                deletion_summary["notes"].append(f"Deleted {items_count} sale item(s)")
                
                # Finally delete the sale
                sale.delete()
                
                return Response({
                    "success": True,
                    "message": f"Sale {sale.reference} has been safely deleted",
                    "deletion_summary": deletion_summary
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {
                    "error": "Failed to delete sale",
                    "message": f"An error occurred while deleting the sale: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def can_delete(self, request, pk=None):
        """
        Check if a sale can be safely deleted and provide information about the deletion impact
        """
        sale = self.get_object()
        
        can_delete = sale.status in ['pending', 'cancelled']
        
        response_data = {
            "can_delete": can_delete,
            "sale_reference": sale.reference,
            "current_status": sale.status,
            "current_status_display": sale.get_status_display(),
            "reason": "Sale can be deleted" if can_delete else f"Sales with status '{sale.get_status_display()}' cannot be deleted"
        }
        
        if can_delete:
            # Provide information about what will happen during deletion
            if sale.status == 'pending':
                response_data.update({
                    "deletion_impact": "No additional actions required - sale is still pending",
                    "will_restore_stock": False,
                    "will_refund_payment": False,
                    "has_payments": bool(sale.paid_amount and sale.paid_amount > 0),
                    "notes": "Pending sales can be deleted without any stock or payment complications"
                })
            elif sale.status == 'cancelled':
                response_data.update({
                    "deletion_impact": "Stock restoration and payment refunds were already processed during cancellation",
                    "will_restore_stock": False,  # Already done during cancellation
                    "will_refund_payment": False,  # Already done during cancellation
                    "has_payments": bool(sale.paid_amount and sale.paid_amount > 0),
                    "paid_amount": float(sale.paid_amount or 0),
                    "notes": "Cancelled sales can be safely deleted - all necessary cleanup was done during cancellation"
                })
        
        return Response(response_data)

# Production serializer and viewset
class ProductionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Production operations
    """
    queryset = Production.objects.all().order_by('-date')
    serializer_class = ProductionSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Auto-generate a reference if not provided
        if not serializer.validated_data.get('reference'):
            # Get the last production record
            last_production = Production.objects.order_by('-id').first()
            # Generate a new reference
            if last_production and last_production.reference:
                # Extract the numeric part of the last reference
                last_num = int(last_production.reference.split('-')[-1])
                new_reference = f"PROD-{last_num + 1:04d}"
            else:
                new_reference = "PROD-0001"
            
            # Set the reference
            serializer.validated_data['reference'] = new_reference
            
        # Set the date if not provided
        if not serializer.validated_data.get('date'):
            serializer.validated_data['date'] = timezone.now().date()
            
        # Save the production
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_material(self, request, pk=None):
        production = self.get_object()
        
        # Validate the request data
        serializer = ProductionMaterialSerializer(data=request.data)
        if serializer.is_valid():
            # Set the production
            serializer.validated_data['production'] = production
            
            # Save the material
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        production = self.get_object()
        
        # Get materials for this production
        materials = ProductionMaterial.objects.filter(production=production)
        
        # Serialize and return
        serializer = ProductionMaterialSerializer(materials, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        production = self.get_object()
        
        try:
            # Get materials for this production
            materials = ProductionMaterial.objects.filter(production=production)
            
            # Check if there are materials
            if not materials.exists():
                return Response(
                    {"error": "No materials associated with this production"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify stock availability for all materials
            for material in materials:
                # Get stock for this product in the specified zone
                stock = Stock.objects.filter(product=material.product, zone=production.zone).first()
                
                # Check if stock exists and has enough quantity
                if not stock or stock.quantity < material.quantity:
                    return Response(
                        {"error": f"Insufficient stock for {material.product.name} in {production.zone.name}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Reduce stock for materials used
            for material in materials:
                # Get stock for this product
                stock = Stock.objects.get(product=material.product, zone=production.zone)
                
                # Reduce stock quantity
                stock.quantity -= material.quantity
                stock.save()
                
                # Create a stock card for the material consumption
                StockCard.objects.create(
                    product=material.product,
                    zone=production.zone,
                    date=timezone.now().date(),
                    transaction_type='production',
                    reference=production.reference,
                    quantity_out=material.quantity,
                    balance=stock.quantity,
                    notes=f"Used in production {production.reference}"
                )
            
            # Increase stock for the produced product
            # Get or create stock for the produced product
            product_stock, created = Stock.objects.get_or_create(
                product=production.product,
                zone=production.zone,
                defaults={'quantity': 0}
            )
            
            # Increase stock quantity
            product_stock.quantity += production.quantity
            product_stock.save()
            
            # Create a stock card for the produced product
            StockCard.objects.create(
                product=production.product,
                zone=production.zone,
                date=timezone.now().date(),
                transaction_type='production',
                reference=production.reference,
                quantity_in=production.quantity,
                balance=product_stock.quantity,
                notes=f"Produced in {production.reference}"
            )
            
            return Response({"status": "Production processed successfully"})
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Serializers et viewsets pour les modèles de Stock
class StockSupplyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock supplies
    """
    queryset = StockSupply.objects.prefetch_related('items__product').all().order_by('-date') # Prefetch items and product
    serializer_class = StockSupplySerializer
    permission_classes = [IsAuthenticated] # Simplified permission for now

    def _update_stock_and_create_card(self, supply_instance):
        """Helper function to update stock and create stock card entries for a completed supply."""
        if supply_instance.status == 'received':
            for item in supply_instance.items.all():
                # Use received_quantity if available and accurate, otherwise fallback to quantity
                # For 'received' status, usually item.quantity is intended.
                quantity_to_add = item.quantity # Assuming full quantity for 'received'

                if quantity_to_add > 0:
                    stock, created = Stock.objects.get_or_create(
                        product=item.product,
                        zone=supply_instance.zone,
                        defaults={'quantity': 0}
                    )
                    # Atomically update stock quantity
                    Stock.objects.filter(pk=stock.pk).update(quantity=F('quantity') + quantity_to_add)
                    stock.refresh_from_db() # Get the updated quantity for the card

                    # Create Stock Card entry
                    StockCard.objects.create(
                        product=item.product,
                        zone=supply_instance.zone,
                        date=supply_instance.date,
                        transaction_type='supply',
                        reference=supply_instance.reference,
                        quantity_in=quantity_to_add,
                        quantity_out=0,
                        unit_price=item.unit_price,
                        balance=stock.quantity, # Use the updated balance
                        notes=f"Supply received: {supply_instance.reference}"
                    )
        # TODO: Add logic for 'partial' status if needed, likely using item.received_quantity increments

    def perform_create(self, serializer):
        """Override perform_create to handle stock update on creation if status is 'received'."""
        # Generate a reference if not provided
        if not serializer.validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Use atomic transaction to prevent race conditions
            with transaction.atomic():
                count = StockSupply.objects.filter(reference__startswith=f'SUP-{datestr}').count()
                reference = f'SUP-{datestr}-{count+1:04d}'
            serializer.validated_data['reference'] = reference
        
        supply = serializer.save(created_by=self.request.user)
        # Check if the supply is created with 'received' status
        if supply.status == 'received':
            self._update_stock_and_create_card(supply)

    def update(self, request, *args, **kwargs):
        """Override update to handle stock update when status changes to 'received'."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save() # Save first

        new_status = updated_instance.status

        # Check if status changed specifically to 'received' from another status
        if old_status != 'received' and new_status == 'received':
            self._update_stock_and_create_card(updated_instance)
        # TODO: Add logic for status changing to 'partial' if needed

        # Return the serialized data of the updated instance
        return Response(serializer.data)

class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name

    class Meta:
        model = StockTransferItem
        fields = ['id', 'transfer', 'product', 'product_name', 'quantity', 'transferred_quantity']
        read_only_fields = ['id', 'product_name'] # Add product_name here
        extra_kwargs = {'transfer': {'required': False}} # Keep this

class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True)
    class Meta:
        model = StockTransfer
        fields = ['id', 'reference', 'from_zone', 'to_zone', 'date', 'status', 'notes', 'created_by', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        transfer = StockTransfer.objects.create(**validated_data)
        for item_data in items_data:
            # Ensure transfer field is not duplicated
            if 'transfer' in item_data:
                item_data.pop('transfer')
            StockTransferItem.objects.create(transfer=transfer, **item_data)
        return transfer

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        instance = super().update(instance, validated_data)
        
        # Keep track of updated items
        updated_item_ids = set()
        
        # Process each item
        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id:
                # Update existing item
                try:
                    item = StockTransferItem.objects.get(id=item_id, transfer=instance)
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                    updated_item_ids.add(item_id)
                except StockTransferItem.DoesNotExist:
                    pass
            else:
                # Create new item - Remove transfer if it exists in item_data
                if 'transfer' in item_data:
                    item_data.pop('transfer')
                StockTransferItem.objects.create(transfer=instance, **item_data)
        
        # Delete items not included in the update
        existing_items = instance.items.all()
        for item in existing_items:
            if item.id not in updated_item_ids and item.id is not None:
                # Only delete if it wasn't just created (has an ID)
                item.delete()
                
        return instance

# Add a new view for stock availability checking
class StockAvailabilityView(views.APIView):
    """
    API endpoint to check if there's enough stock for a product in a specific zone
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        product_id = request.query_params.get('product')
        zone_id = request.query_params.get('zone')
        quantity = request.query_params.get('quantity')
        
        if not all([product_id, zone_id, quantity]):
            return Response(
                {'error': 'Missing required parameters: product, zone, and quantity are all required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_id = int(product_id)
            zone_id = int(zone_id)
            quantity = float(quantity)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid parameters: product and zone must be integers, quantity must be a number.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock = Stock.objects.get(product_id=product_id, zone_id=zone_id)
            available = stock.quantity >= quantity
            
            return Response({
                'available': available,
                'stock': stock.quantity,
                'product_id': product_id,
                'zone_id': zone_id,
                'requested': quantity
            })
        except Stock.DoesNotExist:
            return Response({
                'available': False,
                'stock': 0,
                'product_id': product_id,
                'zone_id': zone_id,
                'requested': quantity
            })

class StockTransferViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock transfers
    """
    queryset = StockTransfer.objects.prefetch_related('items__product').all().order_by('-date') # Prefetch items
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated] # Simplified permission for now

    def perform_create(self, serializer):
        """Set the creator on creation and generate reference if needed."""
        # Generate a reference if not provided
        if not serializer.validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Use atomic transaction to prevent race conditions
            with transaction.atomic():
                count = StockTransfer.objects.filter(reference__startswith=f'TRF-{datestr}').count()
                reference = f'TRF-{datestr}-{count+1:04d}'
            serializer.validated_data['reference'] = reference
            print(f"[View Create] Generated reference in view: {reference}")
            
        # Set the creator
        transfer = serializer.save(created_by=self.request.user)
        
        # Check if the transfer is created with 'completed' status
        if transfer.status == 'completed':
            self._process_stock_transfer(transfer)

    def _process_stock_transfer(self, transfer_instance):
        """Helper function to update stock and create stock card entries for a completed transfer."""
        print(f"Processing transfer {transfer_instance.reference}")
        
        if transfer_instance.status != 'completed':
            print(f"Transfer status is {transfer_instance.status}, not processing")
            return
        
        # Check if there are items to process
        items = list(transfer_instance.items.all())
        if not items:
            print(f"No items to process for transfer {transfer_instance.reference}")
            return
        
        print(f"Found {len(items)} items to process")
        
        try:
            with transaction.atomic():
                print(f"Starting atomic transaction")
                
                for item in items:
                    print(f"Processing item: {item.id} - {item.product.name}")
                    
                    # Use transferred_quantity if it's set, otherwise use quantity
                    transfer_qty = item.transferred_quantity or item.quantity
                    
                    if transfer_qty <= 0:
                        print(f"Skipping item with zero/negative quantity: {transfer_qty}")
                        continue
                    
                    # Get or create source stock with select_for_update to prevent race conditions
                    source_stock = Stock.objects.select_for_update().get_or_create(
                        product=item.product,
                        zone=transfer_instance.from_zone,
                        defaults={'quantity': 0}
                    )[0]
                    
                    # Get or create destination stock with select_for_update
                    dest_stock = Stock.objects.select_for_update().get_or_create(
                        product=item.product,
                        zone=transfer_instance.to_zone,
                        defaults={'quantity': 0}
                    )[0]
                    
                    print(f"Source stock: {source_stock.quantity}, Dest stock: {dest_stock.quantity}, Transfer: {transfer_qty}")
                    
                    # Verify sufficient stock in source location
                    if source_stock.quantity < transfer_qty:
                        error_msg = f"Stock insuffisant pour {item.product.name}. Disponible: {source_stock.quantity}, Demandé: {transfer_qty}"
                        print(f"ERROR: {error_msg}")
                        raise serializers.ValidationError(error_msg)
                    
                    # Update stock quantities using F() expressions
                    original_source_qty = source_stock.quantity
                    original_dest_qty = dest_stock.quantity
                    
                    Stock.objects.filter(pk=source_stock.pk).update(quantity=F('quantity') - transfer_qty)
                    source_stock.refresh_from_db()
                    
                    Stock.objects.filter(pk=dest_stock.pk).update(quantity=F('quantity') + transfer_qty)
                    dest_stock.refresh_from_db()
                    
                    print(f"Updated stock - Source: {original_source_qty} → {source_stock.quantity}, Dest: {original_dest_qty} → {dest_stock.quantity}")
                    
                    # Create stock card entries
                    source_card = StockCard.objects.create(
                        product=item.product,
                        zone=transfer_instance.from_zone,
                        date=transfer_instance.date,
                        transaction_type='transfer_out',
                        reference=transfer_instance.reference,
                        quantity_out=transfer_qty,
                        balance=source_stock.quantity,
                        notes=f"Transfert vers {transfer_instance.to_zone.name}"
                    )
                    
                    dest_card = StockCard.objects.create(
                        product=item.product,
                        zone=transfer_instance.to_zone,
                        date=transfer_instance.date,
                        transaction_type='transfer_in',
                        reference=transfer_instance.reference,
                        quantity_in=transfer_qty,
                        balance=dest_stock.quantity,
                        notes=f"Transfert depuis {transfer_instance.from_zone.name}"
                    )
                    
                    # Update the transferred_quantity on the item if used
                    if not item.transferred_quantity or item.transferred_quantity != transfer_qty:
                        item.transferred_quantity = transfer_qty
                        item.save()
                    
                    print(f"Created stock cards - Source: {source_card.id}, Dest: {dest_card.id}")
                
                print(f"Transfer processing completed successfully")
        
        except serializers.ValidationError as e:
            print(f"Validation error: {str(e)}")
            raise e
        except Exception as e:
            print(f"Error processing transfer: {str(e)}")
            raise serializers.ValidationError(f"Une erreur s'est produite lors du traitement du transfert: {str(e)}")
   
    def update(self, request, *args, **kwargs):
        """Override update to handle stock processing when status changes to 'completed'."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_instance = serializer.save() # Save first
            new_status = updated_instance.status

            # Check if status changed specifically to 'completed' from another status
            if old_status != 'completed' and new_status == 'completed':
                self._process_stock_transfer(updated_instance)

            # Return the serialized data of the updated instance
            return Response(serializer.data)

        except serializers.ValidationError as e:
            # If stock processing failed (e.g., insufficient stock), return validation error
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Catch other potential errors during processing
            return Response({"error": f"An error occurred during transfer processing: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True) # Add product name

    class Meta:
        model = InventoryItem
        fields = ['id', 'inventory', 'product', 'product_name', 'expected_quantity', 'actual_quantity', 'difference', 'notes']
        read_only_fields = ['id', 'product_name', 'difference'] 
        extra_kwargs = {'inventory': {'required': False}} # Make inventory field not required

class InventorySerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True) # Allow writing items
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Inventory
        fields = ['id', 'reference', 'zone', 'zone_name', 'date', 'status', 'notes',
                  'created_by', 'created_by_name', 'items']
        read_only_fields = ['id', 'zone_name', 'created_by_name']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        inventory = Inventory.objects.create(**validated_data)
        for item_data in items_data:
            # Calculate difference before saving item
            # Fetch current stock quantity to set expected_quantity automatically
            try:
                stock = Stock.objects.get(product=item_data['product'], zone=inventory.zone)
                expected = stock.quantity
            except Stock.DoesNotExist:
                expected = 0
            item_data['expected_quantity'] = expected # Set expected quantity based on current stock

            counted = item_data.get('actual_quantity', 0)
            item_data['difference'] = counted - expected
            InventoryItem.objects.create(inventory=inventory, **item_data)
        return inventory

    def update(self, instance, validated_data):
        # Extract items_data before updating the inventory instance
        items_data = validated_data.pop('items', [])
        
        # Update basic inventory fields
        instance = super().update(instance, validated_data)

        # First, delete all existing items to avoid duplication
        # This ensures we completely replace items instead of just adding to them
        instance.items.all().delete()
        
        # Now create all items fresh from the provided data
        for item_data in items_data:
            # Recalculate difference
            try:
                stock = Stock.objects.get(product=item_data['product'], zone=instance.zone)
                expected = stock.quantity
            except Stock.DoesNotExist:
                expected = 0
                
            item_data['expected_quantity'] = expected
            counted = item_data.get('actual_quantity', 0)
            item_data['difference'] = counted - expected
            
            # Create new item with correct inventory reference
            InventoryItem.objects.create(inventory=instance, **item_data)
        
        instance.refresh_from_db()
        return instance

class InventoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for inventories (stock counts)
    """
    queryset = Inventory.objects.prefetch_related('items__product').all().order_by('-date') # Prefetch items
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated] # Simplified permission

    def perform_create(self, serializer):
        """Set the creator on creation."""
        # Generate a reference if not provided
        if not serializer.validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Use atomic transaction to prevent race conditions
            with transaction.atomic():
                count = Inventory.objects.filter(reference__startswith=f'INV-{datestr}').count()
                reference = f'INV-{datestr}-{count+1:04d}'
            serializer.validated_data['reference'] = reference
            print(f"[View Create] Generated reference in view: {reference}")
        
        # Set the user as creator
        serializer.save(created_by=self.request.user)

    def _process_inventory_adjustment(self, inventory_instance):
        """Helper function to adjust stock based on inventory count differences."""
        if inventory_instance.status == 'completed':
            with transaction.atomic():
                for item in inventory_instance.items.all():
                    difference = item.difference

                    if difference == 0:
                        continue # No adjustment needed

                    # Get or create stock record, ensuring it's locked for update
                    stock, created = Stock.objects.select_for_update().get_or_create(
                        product=item.product,
                        zone=inventory_instance.zone,
                        defaults={'quantity': 0}
                    )

                    # Atomically adjust stock quantity by the difference
                    Stock.objects.filter(pk=stock.pk).update(quantity=F('quantity') + difference)
                    stock.refresh_from_db() # Get the updated quantity

                    # Create Stock Card entry for the adjustment
                    StockCard.objects.create(
                        product=item.product,
                        zone=inventory_instance.zone,
                        date=inventory_instance.date,
                        transaction_type='inventory', # Use 'inventory' type for adjustments
                        reference=inventory_instance.reference,
                        quantity_in=difference if difference > 0 else 0,
                        quantity_out=abs(difference) if difference < 0 else 0,
                        balance=stock.quantity, # Use the final balance
                        notes=f"Inventory Adjustment: {inventory_instance.reference} (Expected: {item.expected_quantity}, Counted: {item.actual_quantity})"
                    )

    def update(self, request, *args, **kwargs):
        """Override update to process stock adjustments when status changes to 'completed'."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_instance = serializer.save() # Save first
            new_status = updated_instance.status

            # Check if status changed specifically to 'completed' from another status
            if old_status != 'completed' and new_status == 'completed':
                self._process_inventory_adjustment(updated_instance)

            return Response(serializer.data)

        except Exception as e:
            # Catch potential errors during processing
            return Response({"error": f"An error occurred during inventory processing: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockCardSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    unit_symbol = serializers.SerializerMethodField()

    class Meta:
        model = StockCard
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'date', 'transaction_type', 'reference',
                  'quantity_in', 'quantity_out', 'unit_price', 'balance', 'unit_symbol', 'notes'] # Add unit_symbol

    def get_unit_symbol(self, obj):
        # Attempt to get the unit symbol from the related product
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None # Return None if symbol cannot be found

class StockCardViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock cards
    """
    queryset = StockCard.objects.all().order_by('-date')
    serializer_class = StockCardSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product')
        zone_id = self.request.query_params.get('zone')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        return queryset

# Serializers et viewsets pour les modèles de Vente
class DeliveryNoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryNoteItem
        fields = ['id', 'delivery_note', 'product', 'quantity']

class DeliveryNoteSerializer(serializers.ModelSerializer):
    items = DeliveryNoteItemSerializer(many=True, read_only=True)
    class Meta:
        model = DeliveryNote
        fields = ['id', 'reference', 'client', 'zone', 'date', 'status', 'notes', 'created_by', 'items']

class DeliveryNoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for delivery notes
    """
    queryset = DeliveryNote.objects.all().order_by('-date')
    serializer_class = DeliveryNoteSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = ['id', 'name', 'description', 'is_active']

class ChargeTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for charge types
    """
    queryset = ChargeType.objects.all().order_by('name')
    serializer_class = ChargeTypeSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

class SaleChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleCharge
        fields = ['id', 'sale', 'charge_type', 'amount', 'description']

class SaleChargeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for sale charges
    """
    queryset = SaleCharge.objects.all()
    serializer_class = SaleChargeSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

# Serializers et viewsets pour les modèles de Tiers
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'name', 'position', 'department', 'email', 'phone', 'address', 'hire_date', 'salary', 'is_active']

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for employees
    """
    queryset = Employee.objects.all().order_by('name')
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

class ClientGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientGroup
        fields = ['id', 'name', 'description', 'discount_percentage', 'is_active']

class ClientGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for client groups
    """
    queryset = ClientGroup.objects.all().order_by('name')
    serializer_class = ClientGroupSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

# Invoice serializer and viewset
class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    sale_reference = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'reference', 'sale', 'sale_reference', 'client_name', 'date', 'due_date', 
                  'status', 'amount', 'paid_amount', 'balance', 'notes']
        read_only_fields = ['id', 'client_name', 'sale_reference']

    def get_client_name(self, obj):
        if obj.sale and obj.sale.client:
            return obj.sale.client.name
        return None

    def get_sale_reference(self, obj):
        if obj.sale:
            return obj.sale.reference
        return None

class InvoiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for invoices
    """
    queryset = Invoice.objects.all().order_by('-date')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Auto-calculate balance based on amount and paid_amount
        if 'amount' in request.data and 'paid_amount' in request.data:
            amount = float(request.data['amount'])
            paid_amount = float(request.data['paid_amount'])
            balance = amount - paid_amount
            serializer.validated_data['balance'] = balance
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # Auto-calculate balance based on amount and paid_amount
        if 'amount' in request.data and 'paid_amount' in request.data:
            amount = float(request.data['amount'])
            paid_amount = float(request.data['paid_amount'])
            request.data['balance'] = amount - paid_amount
        elif 'paid_amount' in request.data:
            amount = instance.amount
            paid_amount = float(request.data['paid_amount'])
            request.data['balance'] = float(amount) - paid_amount
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

# Quote serializer and viewset
class QuoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'quote', 'product', 'product_name', 'quantity', 'unit_price', 'discount_percentage', 'total_price']
        read_only_fields = ['id']
        extra_kwargs = {'quote': {'required': False}}

class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True)
    client_name = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = ['id', 'reference', 'client', 'client_name', 'date', 'expiry_date', 'status',
                  'subtotal', 'tax_amount', 'total_amount', 'notes', 'items']
        read_only_fields = ['id', 'client_name']

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.name
        return None

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        quote = Quote.objects.create(**validated_data)
        # Create QuoteItem records
        for item_data in items_data:
            QuoteItem.objects.create(quote=quote, **item_data)
        return quote

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        # Update the quote instance
        instance = super().update(instance, validated_data)
        # Update or create QuoteItem records
        existing_items = {item.id: item for item in instance.items.all()}
        # Process each item in the update data
        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items[item_id]
                for attr, value in item_data.items():
                    setattr(item, attr, value)
                item.save()
                existing_items.pop(item_id)
            else:
                # Create new item
                QuoteItem.objects.create(quote=instance, **item_data)
        # Delete items not included in the update
        for item in existing_items.values():
            item.delete()
        return instance

class QuoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for quotes
    """
    queryset = Quote.objects.prefetch_related('items__product').all().order_by('-date')
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    @action(detail=True, methods=['post'])
    def convert_to_sale(self, request, pk=None):
        quote = self.get_object()
        # Check if the quote has already been converted
        if quote.status == 'accepted':
            return Response(
                {"error": "This quote has already been converted to a sale"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the zone instance from the provided zone ID
        zone_id = request.data.get('zone')
        if not zone_id:
            return Response(
                {"error": "Zone is required to convert quote to sale"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zone = Zone.objects.get(id=zone_id)
        except Zone.DoesNotExist:
            return Response(
                {"error": "Invalid zone ID provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a new sale with data from the quote
        sale = Sale.objects.create(
            reference=f"S-{quote.reference}",
            client=quote.client,
            zone=zone,  # Use the Zone instance, not the ID
            date=timezone.now().date(),
            status='payment_pending',  # Set to payment_pending when sale is confirmed
            subtotal=quote.subtotal,
            discount_amount=0,  # Can be calculated from items if needed
            tax_amount=quote.tax_amount,
            total_amount=quote.total_amount,
            notes=f"Created from quote {quote.reference}",
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
        # Update the quote status
        quote.status = 'accepted'
        quote.save()
        
        # Return the sale data that the frontend expects
        from .serializers import SaleSerializer
        sale_serializer = SaleSerializer(sale)
        return Response(sale_serializer.data, status=status.HTTP_201_CREATED)

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from .models import UserProfile, Zone
from .serializers import UserSerializer, GroupSerializer, PermissionSerializer, ZoneSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users management
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Filter by username
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(username__icontains=username)
        
        # Filter by role (from UserProfile)
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(profile__role=role)
            
        # Filter by zone (from UserProfile)
        zone = self.request.query_params.get('zone', None)
        if zone:
            queryset = queryset.filter(profile__zone=zone)
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get the currently authenticated user
        """
        # Get the user from the request
        user = request.user
        serializer = self.get_serializer(user)
        data = serializer.data
        
        # Add permissions to the response
        permissions_list = list(user.get_all_permissions())
        data['permissions'] = permissions_list
        
        # Check if user is superuser
        data['is_superuser'] = user.is_superuser
        
        return Response(data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def user_permissions(self, request):
        """
        Returns the permissions for the authenticated user.
        This is used by the frontend to control access to features.
        """
        user = request.user
        # Get all permissions assigned to the user
        user_permissions = user.get_all_permissions()
        
        # Provide simplified permissions (without app_label) which is what we'll use
        simplified_permissions = [perm.split('.')[1] for perm in user_permissions]
        
        # Check if user is admin (superuser)
        is_admin = user.is_superuser
        
        # Get the user's role if available
        role = None
        if hasattr(user, 'profile'):
            role = user.profile.role
        
        return Response({
            'permissions': simplified_permissions,
            'is_admin': is_admin,
            'role': role
        })
    
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password')
        
        if not password:
            return Response(
                {"error": "Password is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(password)
        user.save()
        return Response({"status": "Password set successfully"})

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for groups management
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def perform_create(self, serializer):
        group = serializer.save()
        # The profile handling is now in the serializer
        
    def perform_update(self, serializer):
        group = serializer.save()
        # The profile handling is now in the serializer
        
    def perform_destroy(self, instance):
        # Clean up the profile if it exists
        try:
            from gestion_api.models import GroupProfile
            profile = GroupProfile.objects.get(group=instance)
            profile.delete()
        except GroupProfile.DoesNotExist:
            pass
        instance.delete()

    def get_queryset(self):
        queryset = Group.objects.all()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Get users in this group
        """
        group = self.get_object()
        users = group.user_set.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_users(self, request, pk=None):
        """
        Add users to this group
        """
        group = self.get_object()
        user_ids = request.data.get('users', [])
        
        if not user_ids:
            return Response({'error': 'User IDs are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(id__in=user_ids)
        for user in users:
            user.groups.add(group)
        return Response({'status': 'users added'})
    
    @action(detail=True, methods=['post'])
    def remove_users(self, request, pk=None):
        """
        Remove users from this group
        """
        group = self.get_object()
        user_ids = request.data.get('users', [])
        
        if not user_ids:
            return Response({'error': 'User IDs are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(id__in=user_ids)
        for user in users:
            user.groups.remove(group)
        return Response({'status': 'users removed'})

    def create(self, request, *args, **kwargs):
        """
        Override create method to add better logging
        """
        print(f"GroupViewSet.create received data:")
        print(f"Request data: {request.data}")
        
        # Check if permissions is in the request data
        if 'permissions' in request.data:
            print(f"Permissions data type: {type(request.data['permissions'])}")
            print(f"Permissions content: {request.data['permissions']}")
        else:
            print("No 'permissions' field in the request data")
            
        # Continue with the normal create
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Override update method to add better logging
        """
        print(f"GroupViewSet.update received data:")
        print(f"Request data: {request.data}")
        
        # Check if permissions is in the request data
        if 'permissions' in request.data:
            print(f"Permissions data type: {type(request.data['permissions'])}")
            print(f"Permissions content: {request.data['permissions']}")
        else:
            print("No 'permissions' field in the request data")
            
        # Continue with the normal update
        return super().update(request, *args, **kwargs)

class ZoneViewSet(viewsets.ModelViewSet):
    """
    API endpoint for zones
    """
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Zone.objects.all()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Get users in this zone
        """
        zone = self.get_object()
        users = User.objects.filter(profile__zone=zone)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

# Currency viewset
class CurrencyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for currencies
    """
    queryset = Currency.objects.all().order_by('name')
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    @action(detail=False, methods=['get'])
    def base_currency(self, request):
        """
        Get the base currency of the system
        """
        base_currency = Currency.objects.filter(is_base=True).first()
        if not base_currency:
            return Response({"error": "No base currency defined"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(base_currency)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_as_base(self, request, pk=None):
        """
        Set this currency as the base currency
        """
        currency = self.get_object()
        # Set all currencies as non-base
        Currency.objects.all().update(is_base=False)
        # Set this currency as base
        currency.is_base = True
        currency.save()
        return Response({"status": f"{currency.name} set as base currency"})

# ExchangeRate viewset
class ExchangeRateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for exchange rates
    """
    queryset = ExchangeRate.objects.all().order_by('-date')
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by from_currency
        from_currency = self.request.query_params.get('from_currency', None)
        if from_currency:
            queryset = queryset.filter(from_currency_id=from_currency)
            
        # Filter by to_currency
        to_currency = self.request.query_params.get('to_currency', None)
        if to_currency:
            queryset = queryset.filter(to_currency_id=to_currency)
            
        # Filter by date
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(date=date)
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get the latest exchange rate for a pair of currencies
        """
        from_currency = request.query_params.get('from_currency')
        to_currency = request.query_params.get('to_currency')
        
        if not from_currency or not to_currency:
            return Response(
                {"error": "Both from_currency and to_currency are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        latest_rate = ExchangeRate.objects.filter(
            from_currency_id=from_currency,
            to_currency_id=to_currency,
            is_active=True
        ).order_by('-date').first()
        
        if not latest_rate:
            return Response(
                {"error": "No exchange rate found for this currency pair"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(latest_rate)
        return Response(serializer.data)

# PaymentMethod viewset
class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    API endpoint for payment methods
    """
    queryset = PaymentMethod.objects.all().order_by('name')
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains(name))
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset

# Account viewset
class AccountViewSet(viewsets.ModelViewSet):
    """
    API endpoint for accounts
    """
    queryset = Account.objects.all().order_by('name')
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains(name))
            
        # Filter by account_type
        account_type = self.request.query_params.get('account_type', None)
        if account_type:
            queryset = queryset.filter(account_type=account_type)
            
        # Filter by currency
        currency = self.request.query_params.get('currency', None)
        if currency:
            queryset = queryset.filter(currency_id=currency)
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Get accounts grouped by type
        """
        account_type = request.query_params.get('type')
        if account_type:
            accounts = Account.objects.filter(account_type=account_type, is_active=True)
            serializer = self.get_serializer(accounts, many=True)
            return Response(serializer.data)
        
        # Group accounts by type
        result = {}
        for account_type, _ in Account.ACCOUNT_TYPES:
            accounts = Account.objects.filter(account_type=account_type, is_active=True)
            serializer = self.get_serializer(accounts, many=True)
            result[account_type] = serializer.data
        return Response(result)

# PriceGroup viewset
class PriceGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for price groups
    """
    queryset = PriceGroup.objects.all().order_by('name')
    serializer_class = PriceGroupSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    @action(detail=True, methods=['get'])
    def clients(self, request, pk=None):
        """
        Get clients in this price group
        """
        price_group = self.get_object()
        clients = Client.objects.filter(price_group=price_group)
        from .serializers import ClientSerializer
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)

# ExpenseCategory viewset
class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for expense categories
    """
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset

# Expense viewset
class ExpenseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for expenses
    """
    queryset = Expense.objects.all().order_by('-date', '-created_at')
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
            
        # Filter by account
        account = self.request.query_params.get('account', None)
        if account:
            queryset = queryset.filter(account_id=account)
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Filter by created_by
        created_by = self.request.query_params.get('created_by', None)
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        Change the status of an expense
        """
        expense = self.get_object()
        new_status = request.data.get('status')
        
        valid_statuses = ['draft', 'pending', 'approved', 'paid', 'cancelled']
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = new_status
        expense.save()
        return Response({"status": f"Expense status changed to {new_status}"})

# ClientPayment viewset
class ClientPaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for client payments
    """
    queryset = ClientPayment.objects.all().order_by('-date', '-created_at')
    serializer_class = ClientPaymentSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by client
        client = self.request.query_params.get('client', None)
        if client:
            queryset = queryset.filter(client_id=client)
            
        # Filter by account
        account = self.request.query_params.get('account', None)
        if account:
            queryset = queryset.filter(account_id=account)
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary_by_client(self, request):
        """
        Get summary of payments by client
        """
        from django.db.models import Sum
        summary = ClientPayment.objects.values('client', 'client__name').annotate(
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        return Response(summary)

# SupplierPayment viewset
class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for supplier payments
    """
    queryset = SupplierPayment.objects.all().order_by('-date', '-created_at')
    serializer_class = SupplierPaymentSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by supplier
        supplier = self.request.query_params.get('supplier', None)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
            
        # Filter by account
        account = self.request.query_params.get('account', None)
        if account:
            queryset = queryset.filter(account_id=account)
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary_by_supplier(self, request):
        """
        Get summary of payments by supplier
        """
        from django.db.models import Sum
        summary = SupplierPayment.objects.values('supplier', 'supplier__name').annotate(
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        return Response(summary)

# AccountTransfer viewset
class AccountTransferViewSet(viewsets.ModelViewSet):
    """
    API endpoint for account transfers
    """
    queryset = AccountTransfer.objects.all().order_by('-date', '-created_at')
    serializer_class = AccountTransferSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by from_account
        from_account = self.request.query_params.get('from_account', None)
        if from_account:
            queryset = queryset.filter(from_account=from_account)
            
        # Filter by to_account
        to_account = self.request.query_params.get('to_account', None)
        if to_account:
            queryset = queryset.filter(to_account=to_account)
            
        # Filter by any account (from or to)
        account = self.request.query_params.get('account', None)
        if account:
            queryset = queryset.filter(
                Q(from_account=account) | Q(to_account=account)
            )
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        return queryset
    
    def perform_create(self, serializer):
        with transaction.atomic():
            # Save the transfer
            transfer = serializer.save(created_by=self.request.user)
            
            # Get references to accounts
            from_account = transfer.from_account
            to_account = transfer.to_account
            amount = transfer.amount
            
            if not from_account or not to_account:
                raise serializers.ValidationError("Both source and destination accounts are required")
            
            # Update source account balance (decrease)
            from_account.current_balance -= amount
            from_account.save()
            
            # Update destination account balance (increase)
            to_account.current_balance += amount 
            to_account.save()
            
            # Create AccountStatement entries for the transfer
            # For the source account (debit)
            AccountStatement.objects.create(
                account=from_account,
                date=transfer.date,
                transaction_type='transfer_out',
                reference=transfer.reference,
                description=f"Transfert vers {to_account.name}: {transfer.notes}",
                debit=amount,
                credit=0,
                balance=from_account.current_balance
            )
            
            # For the destination account (credit)
            AccountStatement.objects.create(
                account=to_account,
                date=transfer.date,
                transaction_type='transfer_in',
                reference=transfer.reference,
                description=f"Transfert depuis {from_account.name}: {transfer.notes}",
                debit=0,
                credit=amount,
                balance=to_account.current_balance
            )
            
            # Create CashFlow entry for the transfer
            CashFlow.objects.create(
                reference=transfer.reference,
                date=transfer.date,
                flow_type='transfer',
                amount=amount,
                description=f"Transfert de {from_account.name} vers {to_account.name}: {transfer.notes}",
                account=to_account,  # Record in the destination account
                related_document_type='AccountTransfer',
                related_document_id=transfer.id,
                created_by=self.request.user
            )

# CashFlow viewset
class CashFlowSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = CashFlow
        fields = ['id', 'reference', 'date', 'flow_type', 'amount', 'description', 
                  'account', 'account_name', 'related_document_type', 'related_document_id', 
                  'created_by', 'created_by_name', 'created_at']

class CashFlowViewSet(viewsets.ModelViewSet):
    """
    API endpoint for cash flows
    """
    queryset = CashFlow.objects.all().order_by('-date', '-created_at')
    serializer_class = CashFlowSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# BankReconciliation viewset
class BankReconciliationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for bank reconciliations
    """
    queryset = BankReconciliation.objects.all().order_by('-created_at')
    serializer_class = BankReconciliationSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# FinancialReport viewset
class FinancialReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for financial reports
    """
    queryset = FinancialReport.objects.all().order_by('-created_at')
    serializer_class = FinancialReportSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

@api_view(['GET'])    
@permission_classes([IsAuthenticated])
def debug_permissions(request):
    """
    Debug endpoint to check currently authenticated user's permissions
    Only available in debug mode
    """
    if not settings.DEBUG:
        return Response({"error": "This endpoint is only available in debug mode"}, status=403)
    
    user = request.user
    
    # Check specific permission if provided
    check_perm = request.query_params.get('check', None)
    if check_perm:
        has_perm = user.has_perm(check_perm)
        return Response({
            'permission': check_perm,
            'has_permission': has_perm
        })
    
    # Get all permissions
    permissions_list = list(user.get_all_permissions())
    permissions_list.sort()
    
    # Group permissions by content type
    grouped_permissions = {}
    for perm in permissions_list:
        app_label, codename = perm.split('.')
        if app_label not in grouped_permissions:
            grouped_permissions[app_label] = []
        grouped_permissions[app_label].append(codename)
        
    user_data = {
        'username': user.username,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
    }
    
    if hasattr(user, 'profile'):
        user_data['role'] = user.profile.role
        if user.profile.group:
            user_data['group'] = user.profile.group.name
        
    return Response({
        'user': user_data,
        'all_permissions': permissions_list,
        'grouped_permissions': grouped_permissions
    })

from rest_framework.views import APIView
from rest_framework.response import Response

class DebugGroupView(APIView):
    """
    Debug endpoint for groups
    """
    def get(self, request):
        groups = Group.objects.all()
        data = []
        
        for group in groups:
            group_data = {
                'id': group.id,
                'name': group.name,
                'permissions': [
                    {
                        'id': perm.id,
                        'name': perm.name,
                        'codename': perm.codename,
                        'app_label': perm.content_type.app_label,
                        'model': perm.content_type.model
                    }
                    for perm in group.permissions.all()
                ]
            }
            data.append(group_data)
        
        return Response(data)

class DebugPermissionView(APIView):
    """
    Debug endpoint for permissions
    """
    def get(self, request):
        permissions = Permission.objects.all()
        data = []
        
        for perm in permissions:
            perm_data = {
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'full_codename': f"{perm.content_type.app_label}.{perm.codename}",
                'app_label': perm.content_type.app_label,
                'model': perm.content_type.model
            }
            data.append(perm_data)
        
        return Response(data)

# ProductCategory viewset
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for product categories
    """
    queryset = ProductCategory.objects.all().order_by('name')
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains(name))
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# UnitOfMeasure viewset
class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    """
    API endpoint for units of measure
    """
    queryset = UnitOfMeasure.objects.all().order_by('name')
    serializer_class = UnitOfMeasureSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by name
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains(name))
            
        # Filter by is_active
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset

# Stock serializer and viewset
class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    unit_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = ['id', 'product', 'product_name', 'zone', 'zone_name', 'quantity', 'unit_symbol', 'updated_at']
    
    def get_product_name(self, obj):
        return obj.product.name if obj.product else None
    
    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone else None
        
    def get_unit_symbol(self, obj):
        try:
            if obj.product and obj.product.unit:
                return obj.product.unit.symbol
        except:
            pass
        return None

class StockViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stock management
    """
    queryset = Stock.objects.all().order_by('product__name')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def get_queryset(self):
        queryset = Stock.objects.all().order_by('product__name')
        
        # Filter by zone if specified
        zone_id = self.request.query_params.get('zone', None)
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
            
        # Filter by product if specified
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
            
        return queryset
        
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get stock for a specific product across all zones"""
        product_id = request.query_params.get('id', None)
        if not product_id:
            return Response({"error": "Product ID is required"}, status=400)
            
        stocks = Stock.objects.filter(product_id=product_id)
        serializer = self.get_serializer(stocks, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def by_zone(self, request, *args, **kwargs):
        """Get all stock for a specific zone"""
        zone_id = self.kwargs.get('zone_id') or request.query_params.get('id')
        if not zone_id:
            return Response({"error": "Zone ID is required"}, status=400)
            
        stocks = Stock.objects.filter(zone_id=zone_id)
        serializer = self.get_serializer(stocks, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def check_availability(self, request):
        """
        Check if there's enough stock for a product in a specific zone
        """
        product_id = request.query_params.get('product')
        zone_id = request.query_params.get('zone')
        quantity = request.query_params.get('quantity', 1)
        
        if not all([product_id, zone_id]):
            return Response(
                {'error': 'Missing required parameters: product and zone are both required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_id = int(product_id)
            zone_id = int(zone_id)
            quantity = float(quantity)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid parameters: product and zone must be integers, quantity must be a number.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock = Stock.objects.get(product_id=product_id, zone_id=zone_id)
            available = stock.quantity >= quantity
            
            return Response({
                'available': available,
                'stock': stock.quantity,
                'product_id': product_id,
                'zone_id': zone_id,
                'requested': quantity
            })
        except Stock.DoesNotExist:
            return Response({
                'available': False,
                'stock': 0,
                'product_id': product_id,
                'zone_id': zone_id,
                'requested': quantity
            })

# CashReceipt serializer and viewset
class CashReceiptSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    sale_reference = serializers.CharField(source='sale.reference', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    # Make reference optional by allowing null/blank values
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CashReceipt
        fields = ['id', 'reference', 'account', 'account_name', 'sale', 'sale_reference', 
                'client', 'client_name', 'date', 'amount', 'description', 'payment_method', 
                'payment_method_name', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'account_name', 'client_name', 'sale_reference', 'payment_method_name']

class CashReceiptViewSet(viewsets.ModelViewSet):
    """
    API endpoint pour les paiements
    """
    queryset = CashReceipt.objects.all().order_by('-date', '-created_at')
    serializer_class = CashReceiptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrer par client
        client_id = self.request.query_params.get('client', None)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Filtrer par vente
        sale_id = self.request.query_params.get('sale', None)
        if sale_id:
            queryset = queryset.filter(sale_id=sale_id)
        
        # Filtrer par compte
        account_id = self.request.query_params.get('account', None)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        # Filtrer par période
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        
        return queryset
    
    def perform_create(self, serializer):
        # Générer automatiquement une référence si non fournie
        if not serializer.validated_data.get('reference'):
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            # Utiliser une transaction atomique pour éviter les conditions de course
            with transaction.atomic():
                count = CashReceipt.objects.filter(reference__startswith=f'RECU-{datestr}').count()
                reference = f'RECU-{datestr}-{count+1:04d}'
            serializer.validated_data['reference'] = reference
        
        with transaction.atomic():
            # Créer l'encaissement
            receipt = serializer.save(created_by=self.request.user)
            
            # Récupérer les objets nécessaires
            account = receipt.account
            client = receipt.client
            sale = receipt.sale
            client_account = client.account if client else None
            amount = receipt.amount
            
            # Mettre à jour le solde du compte de caisse
            if account:
                account.current_balance += Decimal(str(amount))
                account.save()
                
                # Créer une entrée dans AccountStatement pour le compte de caisse
                AccountStatement.objects.create(
                    account=account,
                    date=receipt.date,
                    transaction_type='cash_receipt',
                    reference=receipt.reference,
                    description=f"Paiement {receipt.reference}" + (f" - Vente {receipt.sale.reference}" if receipt.sale else "") + (f" - Client {client.name}" if client else ""),
                    credit=amount,
                    debit=0,
                    balance=account.current_balance
                )
              # Si un client est associé, mettre à jour son compte et créer une entrée double d'AccountStatement
            if client_account:
                # Le paiement réduit la dette du client ou augmente son crédit
                client_account.current_balance += amount
                client_account.save()
                
                # Créer un enregistrement AccountStatement pour le compte client (double entrée comptable)
                AccountStatement.objects.create(
                    account=client_account,
                    date=receipt.date,
                    transaction_type='cash_receipt',
                    reference=receipt.reference,
                    description=f"Paiement client {receipt.reference}" + (f" - Vente {receipt.sale.reference}" if receipt.sale else ""),
                    debit=amount,
                    credit=0,
                    balance=client_account.current_balance
                )
            
            # Si lié à une vente, mettre à jour le statut de paiement
            if sale:
                total_payments = CashReceipt.objects.filter(sale=sale).aggregate(Sum('amount'))['amount__sum'] or 0
                # Ajouter le paiement actuel si c'est un nouvel enregistrement (pas dans l'agrégation)
                if receipt.id is None:
                    total_payments += amount
                
                # Mettre à jour le statut de paiement
                if total_payments >= sale.total_amount:
                    sale.payment_status = 'paid'
                elif total_payments > 0:
                    sale.payment_status = 'partially_paid'
                
                sale.save()
            
            # Créer une entrée dans CashFlow
            CashFlow.objects.create(
                reference=receipt.reference,
                date=receipt.date,
                flow_type='income',
                amount=amount,
                description=receipt.description or f"Paiement {receipt.reference}" + (f" - Vente {receipt.sale.reference}" if receipt.sale else ""),
                account=account,
                related_document_type='sale' if receipt.sale else 'cash_receipt',
                related_document_id=receipt.sale.id if receipt.sale else receipt.id,
                created_by=self.request.user
            )
    
    @action(detail=False, methods=['post'])
    def from_sale(self, request):
        """
        Créer un encaissement à partir d'une vente
        """
        try:
            sale_id = request.data.get('sale')
            sale = Sale.objects.get(id=sale_id)
            
            account_id = request.data.get('account')
            account = Account.objects.get(id=account_id)
            
            amount = request.data.get('amount')
            date = request.data.get('date', timezone.now().date())
            payment_method_id = request.data.get('payment_method')
            payment_method = PaymentMethod.objects.get(id=payment_method_id) if payment_method_id else None
            
            # Générer la référence
            today = timezone.now()
            datestr = today.strftime("%Y%m%d")
            with transaction.atomic():
                count = CashReceipt.objects.filter(reference__startswith=f'RECU-{datestr}').count()
                reference = f'RECU-{datestr}-{count+1:04d}'
            
            # Créer l'encaissement
            receipt = CashReceipt.objects.create(
                reference=reference,
                sale=sale,
                client=sale.client,
                account=account,
                date=date,
                amount=amount,
                payment_method=payment_method,
                description=f"Paiement pour la vente {sale.reference}",
                created_by=request.user
            )
            
            # Mettre à jour le solde du compte de caisse et client
            account_id = request.data.get('account')
            account = Account.objects.get(id=account_id)
            
            # Mettre à jour le solde du compte de caisse
            if account:
                account.current_balance += float(amount)
                account.save()
                
                AccountStatement.objects.create(
                    account=account,
                    date=receipt.date,
                    transaction_type='cash_receipt',
                    reference=receipt.reference,
                    description=f"Paiement {receipt.reference} - Vente {sale.reference}",
                    credit=amount,
                    debit=0,
                    balance=account.current_balance
                )
            
            # Mettre à jour le compte client si applicable
            client_account = sale.client.account if sale.client and hasattr(sale.client, 'account') else None
            if client_account:
                client_account.current_balance += float(amount)
                client_account.save()
                
                AccountStatement.objects.create(
                    account=client_account,
                    date=receipt.date,
                    transaction_type='client_payment',
                    reference=receipt.reference,
                    description=f"Paiement client {receipt.reference} - Vente {sale.reference}",
                    debit=amount,
                    credit=0,
                    balance=client_account.current_balance
                )
            
            # Mettre à jour le statut de paiement de la vente
            total_paid = CashReceipt.objects.filter(sale=sale).aggregate(Sum('amount'))['amount__sum'] or 0
            
            if total_paid >= sale.total_amount:
                sale.payment_status = 'paid'
            elif total_paid > 0:
                sale.payment_status = 'partially_paid'
            
            sale.save()
            
            # Créer l'entrée CashFlow
            CashFlow.objects.create(
                reference=receipt.reference,
                date=receipt.date,
                flow_type='income',
                amount=amount,
                description=f"Paiement {receipt.reference} - Vente {sale.reference}",
                account=account,
                related_document_type='sale',
                related_document_id=sale.id,
                created_by=request.user
            )
            
            serializer = CashReceiptSerializer(receipt)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AccountStatementSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = AccountStatement
        fields = ['id', 'account', 'account_name', 'date', 'transaction_type', 'transaction_type_display',
                  'reference', 'description', 'debit', 'credit', 'balance']

class AccountStatementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for account statements (movements)
    """
    queryset = AccountStatement.objects.all().order_by('-date', 'account')
    serializer_class = AccountStatementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by account
        account_id = self.request.query_params.get('account', None)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
            
        # Filter by transaction type
        transaction_type = self.request.query_params.get('transaction_type', None)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset
        
    @action(detail=False, methods=['get'])
    def client_balance(self, request):
        """
        Get account statement and balance for a specific client
        """
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response(
                {"error": "client_id parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response(
                {"error": f"Client with id {client_id} does not exist"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        if not client.account:
            return Response(
                {"error": f"Client {client.name} does not have an associated account"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get account statements for this client's account
        statements = AccountStatement.objects.filter(
            account=client.account
        ).order_by('-date')
        
        # Get current balance
        current_balance = client.account.current_balance
        
        # Optional date range filtering
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        if start_date and end_date:
            statements = statements.filter(date__range=[start_date, end_date])
        
        # Get sales with outstanding balance
        outstanding_sales = Sale.objects.filter(
            client=client, 
            payment_status__in=['unpaid', 'partially_paid']
        ).exclude(status='pending').order_by('-date').order_by('-date')
        
        # Serialize sales with outstanding balance
        outstanding_sales_data = []
        for sale in outstanding_sales:
            # Get paid amount from the sale object
            outstanding_sales_data.append({
                'id': sale.id,
                'reference': sale.reference,
                'date': sale.date.strftime('%Y-%m-%d'),
                'total_amount': float(sale.total_amount),
                'paid_amount': float(sale.paid_amount),
                'balance': float(sale.remaining_amount) if sale.remaining_amount is not None else float(sale.total_amount) - float(sale.paid_amount),
                'payment_status': sale.payment_status
            })
        
        # Serialize the statements
        serializer = self.get_serializer(statements, many=True)
        
        # Return combined data
        return Response({
            'client': {
                'id': client.id,
                'name': client.name,
                'account_id': client.account.id,
                'account_name': client.account.name,
                'current_balance': float(current_balance)
            },
            'statements': serializer.data,
            'outstanding_sales': outstanding_sales_data
        })
