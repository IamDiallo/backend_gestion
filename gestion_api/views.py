from datetime import datetime, timedelta, date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, status, views
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Product, Client, Supplier, Sale, SaleItem, UserProfile, ProductCategory,
    Production, ProductionMaterial, StockSupply, StockSupplyItem, StockTransfer,
    StockTransferItem, Inventory, InventoryItem, StockCard, UnitOfMeasure,
    Zone, Currency, PaymentMethod, Account, PriceGroup, 
    ExpenseCategory, Expense, ClientPayment, SupplierPayment, AccountTransfer, 
    Stock, DeliveryNote,
    DeliveryNoteItem, ChargeType, SaleCharge, Employee, ClientGroup,
    Invoice, Quote, QuoteItem, CashReceipt, SupplierCashPayment, AccountStatement
)
from .serializers import (
    ProductSerializer, ClientSerializer, SupplierSerializer, SaleSerializer, 
    UserProfileSerializer, UserSerializer, PermissionSerializer, GroupSerializer, ZoneSerializer,
    CurrencySerializer, PaymentMethodSerializer,
    AccountSerializer, PriceGroupSerializer, ExpenseCategorySerializer,
    ExpenseSerializer, ClientPaymentSerializer, SupplierPaymentSerializer,
    ProductCategorySerializer, UnitOfMeasureSerializer,
    ProductionSerializer, StockSupplySerializer, StockTransferSerializer, 
    InventorySerializer, StockCardSerializer, DeliveryNoteSerializer,
    ChargeTypeSerializer, SaleChargeSerializer, EmployeeSerializer,
    ClientGroupSerializer, InvoiceSerializer, QuoteSerializer, StockSerializer,
    CashReceiptSerializer, SupplierCashPaymentSerializer, AccountStatementSerializer, PasswordChangeSerializer
)


class HasGroupPermission(BasePermission):
    """Custom permission to check if user has the right permissions to manage groups"""
    
    def has_permission(self, request, view):
        if request.method == 'GET':
            return True
        
        if not request.user.is_authenticated:
            return False
            
        if request.user.is_superuser:
            return True
            
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            return True
            
        if view.action == 'create':
            return request.user.has_perm('auth.add_group')
        elif view.action in ['update', 'partial_update']:
            return request.user.has_perm('auth.change_group')
        elif view.action == 'destroy':
            return request.user.has_perm('auth.delete_group')
        
        return False


# Dashboard API views
@api_view(['GET', 'OPTIONS'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def dashboard_stats(request):
    """Get dashboard statistics"""
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
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
        start_date = datetime(today.year, 1, 1).date()
        end_date = datetime(today.year, 12, 31).date()
    
    if not isinstance(start_date, date):
        start_date = today - timedelta(days=30)
    if not isinstance(end_date, date):
        end_date = today
    
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
    """Get recent sales for dashboard"""
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
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
    """Get low stock items for dashboard"""
    low_stock = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0
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
        for stock in low_stock[:10]
    ]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def inventory_dashboard(request):
    """Get inventory statistics for dashboard"""
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
    
    inventory_value = Stock.objects.annotate(
        value=F('quantity') * F('product__purchase_price')
    ).aggregate(total=Sum('value'))['total'] or 0
    
    low_stock_products = Stock.objects.filter(
        quantity__lt=F('product__min_stock_level'),
        product__min_stock_level__gt=0
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
    
    product_stock_values = Stock.objects.select_related('product', 'zone', 'product__unit').annotate(
        stock_value=F('quantity') * F('product__purchase_price')
    ).filter(
        quantity__gt=0
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
    
    recent_movements = StockCard.objects.filter(date__gte=start_date, date__lte=end_date)
    
    inflow = recent_movements.aggregate(total=Sum('quantity_in'))['total'] or 0
    outflow = recent_movements.aggregate(total=Sum('quantity_out'))['total'] or 0
    
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
    
    historical_value = []
    current_date = datetime.now().date()
    
    for i in range(6, -1, -1):
        target_date = current_date.replace(day=1) - timedelta(days=i * 30)
        target_date = target_date.replace(day=1)
        
        movements_until_date = StockCard.objects.filter(
            date__lte=target_date + timedelta(days=32)
        ).aggregate(
            total_in=Sum('quantity_in'),
            total_out=Sum('quantity_out')
        )
        
        movement_factor = Decimal('1.0')
        if movements_until_date['total_in'] and movements_until_date['total_out']:
            movement_factor = Decimal('0.7') + (Decimal(str(i)) * Decimal('0.05'))
        
        historical_inventory_value = int(inventory_value * movement_factor)
        
        historical_value.append({
            'name': target_date.strftime('%b'),
            'value': historical_inventory_value
        })
    
    return Response({
        'inventory_value': inventory_value,
        'low_stock_products': low_stock_data,
        'product_stock_values': product_stock_data,
        'inflow': inflow,
        'outflow': outflow,
        'category_data': category_data,
        'zone_data': zone_data,
        'historical_value': historical_value
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def reports_sales(request):
    """Get sales report data"""
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


# ViewSets
class UserProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles"""
    queryset = UserProfile.objects.all().select_related('user', 'zone')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        profile = self.get_object()
        serializer = PasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            if not profile.user.check_password(serializer.validated_data['old_password']):
                return Response({'old_password': ['Wrong password.']}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            profile.user.set_password(serializer.validated_data['new_password'])
            profile.user.save()
            return Response({'message': 'Password changed successfully.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def check_permission(self, request, pk=None):
        profile = self.get_object()
        permission_code = request.query_params.get('permission')
        
        if not permission_code:
            return Response({'error': 'Permission code is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        has_permission = profile.has_permission(permission_code)
        return Response({'has_permission': has_permission})


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for users management"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(id=self.request.user.id)
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def user_permissions(self, request):
        """Get current user permissions"""
        user = request.user
        permissions = []
        
        if user.is_superuser:
            permissions = list(Permission.objects.values_list('codename', flat=True))
        else:
            # Get permissions from groups
            permissions = list(user.user_permissions.values_list('codename', flat=True))
            group_permissions = list(Permission.objects.filter(
                group__user=user
            ).values_list('codename', flat=True))
            permissions.extend(group_permissions)
        
        return Response({'permissions': list(set(permissions))})
    
    @action(detail=True, methods=['post'])
    def update_groups(self, request, pk=None):
        """Update user groups"""
        user = self.get_object()
        group_ids = request.data.get('groups', [])
        
        try:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)
            return Response({'message': 'User groups updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for permissions (read-only)"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
            
    @action(detail=False, methods=['get'])
    def categorized(self, request):
        """Get permissions organized by content type"""
        permissions = Permission.objects.select_related('content_type').all()
        
        categorized = {}
        for permission in permissions:
            app_label = permission.content_type.app_label
            model_name = permission.content_type.model
            
            if app_label not in categorized:
                categorized[app_label] = {}
            
            if model_name not in categorized[app_label]:
                categorized[app_label][model_name] = []
            
            categorized[app_label][model_name].append({
                'id': permission.id,
                'name': permission.name,
                'codename': permission.codename
            })
        
        return Response(categorized)


class GroupViewSet(viewsets.ModelViewSet):
    """API endpoint for user groups"""
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasGroupPermission]
    
    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to create group: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
                
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to update group: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def destroy(self, request, *args, **kwargs):
        try:
            response = super().destroy(request, *args, **kwargs)
            return response
        except Exception as e:
            return Response(
                {'error': f'Failed to delete group: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        
        try:
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.add(*permissions)
            return Response({'message': f'Added {len(permissions)} permissions to group'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        
        try:
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.remove(*permissions)
            return Response({'message': f'Removed {len(permissions)} permissions from group'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        group = self.get_object()
        users = group.user_set.all()
        
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active
            })
        
        return Response(user_data)


class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products"""
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not request.data.get('reference'):
            try:
                latest_product = Product.objects.latest('id')
                next_id = latest_product.id + 1
            except Product.DoesNotExist:
                next_id = 1
            
            request.data['reference'] = f'PRD-{next_id:06d}'
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return response

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Generate QR code for product"""
        product = self.get_object()
        
        try:
            import qrcode
            from io import BytesIO
            
            qr_data = product.generate_qr_code_data()
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            response = HttpResponse(buffer.getvalue(), content_type='image/png')
            response['Content-Disposition'] = f'attachment; filename="qr_code_{product.reference}.png"'
            return response
            
        except ImportError:
            return Response(
                {'error': 'QR code generation not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class ZoneViewSet(viewsets.ModelViewSet):
    """API endpoint for zones"""
    queryset = Zone.objects.all().order_by('name')
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ClientViewSet(viewsets.ModelViewSet):
    """API endpoint for clients"""
    queryset = Client.objects.all().order_by('name')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]


class SupplierViewSet(viewsets.ModelViewSet):
    """API endpoint for suppliers"""
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


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
            return Response({'error': 'company_account parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
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
                    return Response({'error': 'No account found for this client'}, status=status.HTTP_400_BAD_REQUEST)
                # Get the company account
                try:
                    company_account = Account.objects.get(id=company_account_id)
                except Account.DoesNotExist:
                    return Response({'error': 'Company account not found'}, status=status.HTTP_400_BAD_REQUEST)
                # Get last statement for client account
                last_client_statement = AccountStatement.objects.filter(account=client_account).order_by('-date', '-id').first()
                previous_client_balance = Decimal(str(last_client_statement.balance)) if last_client_statement else Decimal('0.00')
                # Get last statement for company account
                last_company_statement = AccountStatement.objects.filter(account=company_account).order_by('-date', '-id').first()
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
    
    @action(detail=False, methods=['get'])
    def outstanding_by_supplier(self, request):
        """Get outstanding sales for a specific supplier"""
        supplier_id = request.query_params.get('supplier_id')
        
        if not supplier_id:
            return Response(
                {'error': 'supplier_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get sales with remaining amount > 0 for this supplier
            # Note: This assumes you have a supplier field on Sale model
            # If not, adjust the filter accordingly
            outstanding_sales = Sale.objects.filter(
                supplier_id=supplier_id,
                remaining_amount__gt=0
            ).select_related('zone').order_by('-date')
            
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


class CurrencyViewSet(viewsets.ModelViewSet):
    """API endpoint for currencies"""
    queryset = Currency.objects.all().order_by('name')
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]



class PaymentMethodViewSet(viewsets.ModelViewSet):
    """API endpoint for payment methods"""
    queryset = PaymentMethod.objects.all().order_by('name')
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]


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


class PriceGroupViewSet(viewsets.ModelViewSet):
    """API endpoint for price groups"""
    queryset = PriceGroup.objects.all().order_by('name')
    serializer_class = PriceGroupSerializer
    permission_classes = [IsAuthenticated]


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for expense categories"""
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


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

class ProductCategoryViewSet(viewsets.ModelViewSet):
    """API endpoint for product categories"""
    queryset = ProductCategory.objects.all().order_by('name')
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    """API endpoint for units of measure"""
    queryset = UnitOfMeasure.objects.all().order_by('name')
    serializer_class = UnitOfMeasureSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ProductionViewSet(viewsets.ModelViewSet):
    """API endpoint for productions"""
    queryset = Production.objects.all().order_by('-date')
    serializer_class = ProductionSerializer
    permission_classes = [IsAuthenticated]

class StockSupplyViewSet(viewsets.ModelViewSet):
    """API endpoint for stock supplies"""
    queryset = StockSupply.objects.all().order_by('-date')
    serializer_class = StockSupplySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Mark a supply as received and create account statements"""
        supply = self.get_object()
        if supply.status == 'received':
            return Response({'error': 'Supply is already confirmed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                supply.status = 'received'
                supply.save(update_fields=['status'])
                serializer = self.get_serializer(supply)
                serializer._update_stock_and_create_stockcard(supply)
                serializer._create_account_statement(supply)

            return Response({'success': True, 'message': 'Supply confirmed and account statement created'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_account_statement(self, supply):
        """Create account statement entries for a confirmed stock supply."""
        # Generate reference
        statement_count = AccountStatement.objects.filter(date=timezone.now().date()).count()
        reference = f"SUP-{timezone.now().strftime('%Y%m%d')}-{statement_count + 1:04d}"

        # Get supplier account
        try:
            supplier_account = Account.objects.get(account_type='supplier', supplier=supply.supplier)
        except Account.DoesNotExist:
            raise ValueError("No account found for this supplier")

        # Company account (optional, e.g., cash/bank account)
        company_account = Account.objects.get(account_type='company', name='Main Account')  # adjust as needed

        # Last balances
        last_supplier_balance = AccountStatement.objects.filter(account=supplier_account).order_by('-date', '-id').first()
        supplier_previous_balance = Decimal(last_supplier_balance.balance) if last_supplier_balance else Decimal('0.00')

        last_company_balance = AccountStatement.objects.filter(account=company_account).order_by('-date', '-id').first()
        company_previous_balance = Decimal(last_company_balance.balance) if last_company_balance else Decimal('0.00')

        total_amount = supply.get_total_amount()  # you'll need a method on StockSupply to calculate total cost

        # Supplier account: credit (we owe them)
        new_supplier_balance = supplier_previous_balance + total_amount
        AccountStatement.objects.create(
            account=supplier_account,
            date=timezone.now().date(),
            transaction_type='supply',
            reference=reference,
            description=f"Supply received - {supply.reference} from {supply.supplier.name}",
            credit=total_amount,
            debit=0,
            balance=new_supplier_balance,
        )
        supplier_account.current_balance = new_supplier_balance
        supplier_account.save(update_fields=['current_balance'])

        # Company account: debit if paying immediately
        new_company_balance = company_previous_balance - total_amount
        AccountStatement.objects.create(
            account=company_account,
            date=timezone.now().date(),
            transaction_type='supply',
            reference=reference,
            description=f"Payment for supply {supply.reference} - {supply.supplier.name}",
            credit=0,
            debit=total_amount,
            balance=new_company_balance,
        )
        company_account.current_balance = new_company_balance
        company_account.save(update_fields=['current_balance'])

    @action(detail=False, methods=['get'])
    def outstanding_by_supplier(self, request):
        """Get outstanding stock supplies for a specific supplier"""
        supplier_id = request.query_params.get('supplier_id')
        
        if not supplier_id:
            return Response(
                {'error': 'supplier_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get supplies with remaining amount > 0 for this supplier
            outstanding_supplies = StockSupply.objects.filter(
                supplier_id=supplier_id,
                remaining_amount__gt=0,
                status='received'
            ).select_related('supplier').order_by('-date')
            
            serializer = self.get_serializer(outstanding_supplies, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Error fetching outstanding supplies: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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



class StockTransferViewSet(viewsets.ModelViewSet):
    """API endpoint for stock transfers"""
    queryset = StockTransfer.objects.all().order_by('-date')
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InventoryViewSet(viewsets.ModelViewSet):
    """API endpoint for inventories"""
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


class StockCardViewSet(viewsets.ModelViewSet):
    """API endpoint for stock cards"""
    queryset = StockCard.objects.all().order_by('-date')
    serializer_class = StockCardSerializer
    permission_classes = [IsAuthenticated]


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


class EmployeeViewSet(viewsets.ModelViewSet):
    """API endpoint for employees"""
    queryset = Employee.objects.all().order_by('name')
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]


class ClientGroupViewSet(viewsets.ModelViewSet):
    """API endpoint for client groups"""
    queryset = ClientGroup.objects.all().order_by('name')
    serializer_class = ClientGroupSerializer
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
            zone=zone,  # Use the Zone instance, not the ID
            date=timezone.now().date(),
            status='payment_pending',  # Set to payment_pending when sale is confirmed
            subtotal=quote.subtotal,
            discount_amount=0,  # Can be calculated from items if needed
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
        
        # Return the sale data that the frontend expects
        sale_serializer = SaleSerializer(sale)
        return Response(sale_serializer.data, status=status.HTTP_201_CREATED)


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
    def by_zone(self, request, zone_id=None):
        """Get stock by zone"""
        if zone_id:
            stock = self.queryset.filter(zone_id=zone_id)
            serializer = self.get_serializer(stock, many=True)
            return Response(serializer.data)
        return Response({'error': 'Zone ID is required'}, status=400)


class CashReceiptViewSet(viewsets.ModelViewSet):
    """API endpoint for cash receipts"""
    queryset = CashReceipt.objects.all()
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


class AccountStatementViewSet(viewsets.ModelViewSet):
    """API endpoint for account statements"""
    queryset = AccountStatement.objects.all()
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
                # Invalid account_id format, return empty queryset
                queryset = AccountStatement.objects.none()
        return queryset

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get ONLY the current balance for an account (DEPRECATED - use account_balance instead)"""
        # This endpoint is kept for backwards compatibility
        # New code should use account_balance endpoint
        id = request.query_params.get('id')
        type = request.query_params.get('type')
        account_id = request.query_params.get('account_id')

        # New API: Get balance by account_id directly
        if account_id:
            try:
                account = Account.objects.get(id=account_id)
                last_statement = AccountStatement.objects.filter(account=account).order_by('-date', '-id').first()
                balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')
                
                return Response({
                    'balance': float(balance),
                    'account_id': account.id
                })
            except Account.DoesNotExist:
                return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response(
                    {'error': f'Error fetching balance: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Old API: Get comprehensive data (kept for backwards compatibility)
        if not id or not type:
            return Response({'error': 'id and type parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if type == 'client':
                info = Client.objects.get(id=id)
            elif type == 'supplier':
                info = Supplier.objects.get(id=id)
            else:   
                return Response({'error': 'Invalid type parameter'}, status=status.HTTP_400_BAD_REQUEST )

            # Ensure client has an account
            if not info.account:
                return Response({'error': 'No account found for this client'}, status=404)

            account = info.account

            # Use only this account for statements and balance
            statements = AccountStatement.objects.filter(account=account).order_by('-date', '-id').values(
                'id', 'account_id', 'date', 'reference', 'transaction_type', 
                'description', 'debit', 'credit', 'balance'
            )[:50]

            # The current balance is the last statement's balance
            last_statement = AccountStatement.objects.filter(account=account).order_by('-date', '-id').first()
            balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')

            # Get outstanding sales for the client
            if type == 'client':
                outstanding_sales = Sale.objects.filter(
                    client=info, 
                    payment_status__in=['unpaid', 'partially_paid']
                ).values(
                    'id', 'reference', 'date', 'total_amount', 'paid_amount', 'payment_status'
                )
            elif type == 'supplier':
                outstanding_sales = []  # Implement supplier outstanding purchases if needed

            # Get total sales and payments for the client
            total_sales = Sale.objects.filter(client=info).aggregate(total=Sum('total_amount'))['total'] or 0
            total_account_credits = AccountStatement.objects.filter(account=account, credit__gt=0).aggregate(total=Sum('credit'))['total'] or 0
            sale_payments_from_account = AccountStatement.objects.filter(account=account, transaction_type='client_payment', debit__gt=0).aggregate(total=Sum('debit'))['total'] or 0

            sales_count = Sale.objects.filter(client=info).count()
            payments_count = AccountStatement.objects.filter(account=account).count()

            # Add transaction_type_display for statements
            transaction_type_choices = {
                'client_payment': 'Règlement client',
                'supplier_payment': 'Règlement fournisseur',
                'transfer_in': 'Virement entrant',
                'transfer_out': 'Virement sortant',
                'cash_receipt': 'Encaissement',
                'cash_payment': 'Décaissement',
                'expense': 'Dépense',
                'sale': 'Vente',
                'purchase': 'Achat',
                'deposit': 'Dépôt'
            }
            for statement in statements:
                statement['transaction_type_display'] = transaction_type_choices.get(
                    statement['transaction_type'], statement['transaction_type']
                )

            return Response({
                'id': info.id,
                'name': info.name,
                'account_id': account.id,
                'total_sales': float(total_sales),
                'total_account_credits': float(total_account_credits),
                'sale_payments_from_account': float(sale_payments_from_account),
                'balance': float(balance),
                'sales_count': sales_count,
                'payments_count': payments_count,
                'outstanding_sales': list(outstanding_sales),
                'statements': list(statements),
            })

        except (Client.DoesNotExist, Supplier.DoesNotExist):
            return Response({'error': 'Client or Supplier not found'}, status=404)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def account_info(self, request):
        """Get comprehensive account info: balance + statements + outstanding sales"""
        account_id = request.query_params.get('account_id')
        entity_type = request.query_params.get('type')  # 'client' or 'supplier'
        
        if not account_id:
            return Response(
                {'error': 'account_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if entity_type not in ['client', 'supplier']:
            return Response(
                {'error': 'type parameter must be "client" or "supplier"'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the account
            account = Account.objects.get(id=account_id)
            
            # Get current balance from last statement
            last_statement = AccountStatement.objects.filter(account=account).order_by('-date', '-id').first()
            balance = Decimal(str(last_statement.balance)) if last_statement else Decimal('0.00')
            
            # Get statements for this account
            statements = AccountStatement.objects.filter(account=account).order_by('-date', '-id')[:50]
            
            # Add transaction_type_display for statements
            transaction_type_choices = {
                'client_payment': 'Règlement client',
                'supplier_payment': 'Règlement fournisseur',
                'transfer_in': 'Virement entrant',
                'transfer_out': 'Virement sortant',
                'cash_receipt': 'Encaissement',
                'cash_payment': 'Décaissement',
                'expense': 'Dépense',
                'sale': 'Vente',
                'purchase': 'Achat',
                'deposit': 'Dépôt',
                'supply': 'Approvisionnement'
            }
            
            statements_data = []
            for statement in statements:
                statements_data.append({
                    'id': statement.id,
                    'account_id': statement.account_id,
                    'date': statement.date,
                    'reference': statement.reference,
                    'transaction_type': statement.transaction_type,
                    'transaction_type_display': transaction_type_choices.get(
                        statement.transaction_type, statement.transaction_type
                    ),
                    'description': statement.description,
                    'debit': str(statement.debit),
                    'credit': str(statement.credit),
                    'balance': str(statement.balance)
                })
            
            # Get outstanding sales/supplies based on entity type
            outstanding_sales_data = []
            outstanding_supplies_data = []
            
            if entity_type == 'client':
                try:
                    client = Client.objects.get(account=account)
                    outstanding_sales = Sale.objects.filter(
                        client=client,
                        remaining_amount__gt=0
                    ).select_related('client', 'zone').order_by('-date')
                    
                    for sale in outstanding_sales:
                        outstanding_sales_data.append({
                            'id': sale.id,
                            'reference': sale.reference,
                            'date': sale.date,
                            'total_amount': str(sale.total_amount),
                            'paid_amount': str(sale.paid_amount),
                            'remaining_amount': str(sale.remaining_amount),
                            'payment_status': sale.payment_status
                        })
                except Client.DoesNotExist:
                    pass
                    
            elif entity_type == 'supplier':
                try:
                    supplier = Supplier.objects.get(account=account)
                    outstanding_supplies = StockSupply.objects.filter(
                        supplier=supplier,
                        remaining_amount__gt=0,
                        status='received'
                    ).select_related('supplier').order_by('-date')
                    
                    for supply in outstanding_supplies:
                        outstanding_supplies_data.append({
                            'id': supply.id,
                            'reference': supply.reference,
                            'date': supply.date,
                            'total_amount': str(supply.total_amount),
                            'paid_amount': str(supply.paid_amount),
                            'remaining_amount': str(supply.remaining_amount),
                            'payment_status': supply.payment_status
                        })
                except Supplier.DoesNotExist:
                    pass
            
            return Response({
                'balance': float(balance),
                'statements': statements_data,
                'outstanding_sales': outstanding_sales_data,
                'outstanding_supplies': outstanding_supplies_data
            })
            
        except Account.DoesNotExist:
            return Response(
                {'error': 'Account not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error fetching account info: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Debug Views
class DebugGroupView(APIView):
    """Debug view for groups"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.contrib.auth.models import Group
        groups = Group.objects.all()
        data = []
        for group in groups:
            data.append({
                'id': group.id,
                'name': group.name,
                'permissions': [p.codename for p in group.permissions.all()]
            })
        return Response(data)


class DebugPermissionView(APIView):
    """Debug view for permissions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.all()
        data = []
        for perm in permissions:
            data.append({
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'content_type': str(perm.content_type)
            })
        return Response(data)


class StockAvailabilityView(APIView):
    """API endpoint to check if there's enough stock for a product in a specific zone"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check stock availability for a product in a zone"""
        product_id = request.query_params.get('product_id')
        zone_id = request.query_params.get('zone_id')
        quantity = request.query_params.get('quantity', 1)
        
        if not product_id or not zone_id:
            return Response({
                'error': 'product_id and zone_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quantity = float(quantity)
            stock = Stock.objects.get(product_id=product_id, zone_id=zone_id)
            available = stock.quantity >= quantity
            
            return Response({
                'available': available,
                'current_stock': stock.quantity,
                'requested_quantity': quantity,
                'product_name': stock.product.name,
                'zone_name': stock.zone.name
            })
        except Stock.DoesNotExist:
            return Response({
                'available': False,
                'current_stock': 0,
                'requested_quantity': quantity,
                'error': 'Stock not found for this product and zone'
            })
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid quantity value'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])    
@permission_classes([IsAuthenticated])
def debug_permissions(request):
    """Debug endpoint to check user permissions"""
    user = request.user
    
    return Response({
        'user': user.username,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'groups': [group.name for group in user.groups.all()],
        'user_permissions': [perm.codename for perm in user.user_permissions.all()],
        'all_permissions': [perm.codename for perm in user.get_all_permissions()],
    })
