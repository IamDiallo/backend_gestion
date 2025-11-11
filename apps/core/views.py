from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from .models import UserProfile, Zone
from .serializers import (
    UserProfileSerializer, UserSerializer, ZoneSerializer,
    GroupSerializer, PermissionSerializer, PasswordChangeSerializer
)


class PasswordChangeSerializer:
    pass  # Import from gestion_api if needed


class HasGroupPermission:
    pass  # Import from gestion_api if needed


class UserProfileViewSet(viewsets.ModelViewSet):
    """API endpoint for user profiles"""
    queryset = UserProfile.objects.all().select_related('user', 'zone')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)
        return queryset


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
            permissions = list(user.user_permissions.values_list('codename', flat=True))
            group_permissions = list(Permission.objects.filter(
                group__user=user
            ).values_list('codename', flat=True))
            permissions.extend(group_permissions)
        
        # Get user role and groups
        role = None
        groups = []
        try:
            profile = user.userprofile
            role = profile.role
        except:
            pass
        
        groups = list(user.groups.values_list('name', flat=True))
        
        return Response({
            'permissions': list(set(permissions)),
            'is_admin': user.is_superuser or user.is_staff,
            'role': role,
            'groups': groups
        })


class ZoneViewSet(viewsets.ModelViewSet):
    """API endpoint for zones"""
    queryset = Zone.objects.all().order_by('name')
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """API endpoint for user groups"""
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for permissions (read-only)"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def categorized(self, request):
        """Get permissions organized by content type (app and model)"""
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
