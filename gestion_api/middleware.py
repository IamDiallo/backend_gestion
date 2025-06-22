import sys
import traceback
import logging
from django.http import JsonResponse
from django.conf import settings
from django.urls import resolve
from .models import UserProfile
import json
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Log the error with structured data
        logger.error(
            f"Exception in request to {request.path}",
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                'exception_type': type(exception).__name__,
                'exception_message': str(exception)
            },
            exc_info=True
        )

        # Return JSON response with error details
        error_response = {
            'error': str(exception),
            'type': type(exception).__name__,
            'detail': traceback.format_exc() if settings.DEBUG else "An error occurred"
        }
        
        return JsonResponse(error_response, status=500)

class PermissionMiddleware:
    """
    Middleware to check permissions for specific API endpoints
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define permission mappings based on URL pattern and HTTP method
        self.permission_map = {
            # Sales module
            'sales-list': {
                'GET': 'view_sale',
                'POST': 'add_sale',
            },
            'sales-detail': {
                'GET': 'view_sale',
                'PUT': 'change_sale',
                'DELETE': 'delete_sale',
            },
            # Clients module
            'clients-list': {
                'GET': 'view_client',
                'POST': 'add_client',
            },
            'clients-detail': {
                'GET': 'view_client',
                'PUT': 'change_client',
                'DELETE': 'delete_client',
            },
            # Products module
            'products-list': {
                'GET': 'view_product',
                'POST': 'add_product',
            },
            'products-detail': {
                'GET': 'view_product',
                'PUT': 'change_product',
                'DELETE': 'delete_product',
            },
            # Add more mappings as needed for other endpoints
        }

    def __call__(self, request):
        # Skip permission check for authentication endpoints
        if request.path.startswith('/api/token/') or request.path == '/api/':
            return self.get_response(request)
            
        # Continue processing if user is not authenticated yet (let DRF handle auth)
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Skip permission check for admin users
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role == 'admin':
                return self.get_response(request)
        except UserProfile.DoesNotExist:
            pass
            
        # Get URL name and check permissions
        url_name = resolve(request.path_info).url_name
        
        if url_name in self.permission_map and request.method in self.permission_map[url_name]:
            required_permission = self.permission_map[url_name][request.method]
            
            # Check if user has required permission
            if not request.user.has_perm(f"gestion_api.{required_permission}"):
                try:
                    profile = UserProfile.objects.get(user=request.user)
                    if not profile.has_permission(required_permission):
                        return JsonResponse({
                            'error': 'Permission denied',
                            'required_permission': required_permission
                        }, status=403)
                except UserProfile.DoesNotExist:
                    return JsonResponse({
                        'error': 'Permission denied',
                        'required_permission': required_permission
                    }, status=403)
        
        return self.get_response(request)

class PermissionValidationMiddleware(MiddlewareMixin):
    """
    Middleware to enforce permission validation for critical operations
    This is a second layer of security beyond the DRF permission classes
    """
    
    # Map HTTP methods to permission types
    METHOD_PERMISSION_MAP = {
        'GET': 'view',
        'POST': 'add',
        'PUT': 'change',
        'PATCH': 'change',
        'DELETE': 'delete',
    }
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for OPTIONS requests or non-API paths
        if request.method == 'OPTIONS' or not request.path.startswith('/api/'):
            return None
            
        # Try to get the authenticated user
        jwt_auth = JWTAuthentication()
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return None
                
            validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
            user = jwt_auth.get_user(validated_token)
            if not user or not user.is_authenticated:
                return None
        except Exception:
            # If authentication fails, let the regular auth process handle it
            return None
            
        # Skip permission check for superusers
        if user.is_superuser:
            return None
            
        # Get resolved URL details to determine the model
        resolved = resolve(request.path_info)
        app_name = resolved.app_name
        url_name = resolved.url_name
        
        # Skip permission check for non-protected views
        if not url_name or url_name.startswith('auth_') or url_name == 'token_obtain_pair' or url_name == 'token_refresh':
            return None
            
        # Extract resource name from URL name
        resource_parts = url_name.split('-')
        resource_name = resource_parts[0] if resource_parts else ""
        
        # Skip checking for unknown resources
        if not resource_name:
            return None
            
        # Determine required permission type based on HTTP method
        if request.method not in self.METHOD_PERMISSION_MAP:
            return None
            
        action = self.METHOD_PERMISSION_MAP[request.method]
        
        # Special case for detail views - check ID in URL
        is_detail_view = bool(view_kwargs.get('pk'))
        
        # Skip public endpoints or endpoints with their own permission checking
        if resource_name in ['docs', 'schema', 'dashboard', 'auth', 'me']:
            return None
            
        # Construct the permission string
        perm_string = f"gestion_api.{action}_{resource_name}"
        
        # Check if user has the required permission
        has_perm = user.has_perm(perm_string)
        
        # If not authorized, return 403
        if not has_perm:
            return JsonResponse({
                'detail': f'You do not have permission to perform this action. Required permission: {perm_string}'
            }, status=403)
            
        return None
