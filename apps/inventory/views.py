from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.utils import timezone
from django.db import transaction
import qrcode
import io
import base64

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


class ProductViewSet(viewsets.ModelViewSet):
    """API endpoint for products"""
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Generate QR code for product"""
        from django.http import HttpResponse
        
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
        from django.db.models import Sum, Q
        from apps.partners.models import Supplier
        
        # Get all pending or partial supplies
        supplies = self.queryset.filter(
            Q(payment_status='unpaid') | Q(payment_status='partial')
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
