from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Client, Supplier, Employee, ClientGroup
from .serializers import ClientSerializer, SupplierSerializer, EmployeeSerializer, ClientGroupSerializer


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
