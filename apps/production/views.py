from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Production, ProductionMaterial
from .serializers import ProductionSerializer, ProductionMaterialSerializer


class ProductionViewSet(viewsets.ModelViewSet):
    """API endpoint for productions"""
    queryset = Production.objects.all().order_by('-date')
    serializer_class = ProductionSerializer
    permission_classes = [IsAuthenticated]


class ProductionMaterialViewSet(viewsets.ModelViewSet):
    """API endpoint for production materials"""
    queryset = ProductionMaterial.objects.all()
    serializer_class = ProductionMaterialSerializer
    permission_classes = [IsAuthenticated]

