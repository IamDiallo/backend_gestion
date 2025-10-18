from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'clients', views.ClientViewSet, basename='client')
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'client-groups', views.ClientGroupViewSet, basename='clientgroup')

urlpatterns = [
    path('', include(router.urls)),
]
