from rest_framework.routers import DefaultRouter
from .views import ProductionViewSet, ProductionMaterialViewSet

router = DefaultRouter()
router.register(r'productions', ProductionViewSet, basename='production')
router.register(r'production-materials', ProductionMaterialViewSet, basename='production-material')

urlpatterns = router.urls
