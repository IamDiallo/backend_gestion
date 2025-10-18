from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    StockViewSet,
    StockSupplyViewSet,
    StockCardViewSet,
    StockTransferViewSet,
    InventoryViewSet,
    StockReturnViewSet
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'stock-supplies', StockSupplyViewSet, basename='stock-supply')
router.register(r'stock-cards', StockCardViewSet, basename='stock-card')
router.register(r'stock-transfers', StockTransferViewSet, basename='stock-transfer')
router.register(r'inventories', InventoryViewSet, basename='inventory')
router.register(r'stock-returns', StockReturnViewSet, basename='stock-return')

urlpatterns = router.urls
