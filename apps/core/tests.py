"""
Tests for Core app - UserProfile, Zone, Authentication
"""
import pytest
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal

from apps.core.models import UserProfile, Zone
from conftest import UserFactory, ZoneFactory


# ============= Model Tests =============

@pytest.mark.django_db
class TestZoneModel:
    """Test Zone model"""
    
    def test_zone_creation(self, zone):
        """Test creating a zone"""
        assert zone.id is not None
        assert zone.name == "Test Zone"
        assert zone.is_active is True
        assert str(zone) == "Test Zone"
    
    def test_zone_update(self, zone):
        """Test updating a zone"""
        zone.name = "Updated Zone"
        zone.save()
        zone.refresh_from_db()
        assert zone.name == "Updated Zone"
    
    def test_zone_deactivation(self, zone):
        """Test deactivating a zone"""
        zone.is_active = False
        zone.save()
        assert zone.is_active is False


@pytest.mark.django_db
class TestUserProfileModel:
    """Test UserProfile model"""
    
    def test_userprofile_creation(self, user_profile):
        """Test creating a user profile"""
        assert user_profile.id is not None
        assert user_profile.role == 'commercial'
        assert user_profile.is_active is True
        assert user_profile.user.username == 'testuser'
    
    def test_userprofile_str(self, user_profile):
        """Test string representation"""
        expected = f"{user_profile.user.username} - {user_profile.role}"
        assert str(user_profile) == expected
    
    def test_admin_has_all_permissions(self, db):
        """Test that admin role has all permissions"""
        admin_user = UserFactory(password='admin123')
        zone = ZoneFactory()
        # Get the profile created by signal and update it
        admin_profile = UserProfile.objects.get(user=admin_user)
        admin_profile.role = 'admin'
        admin_profile.zone = zone
        admin_profile.save()
        
        # Admin should have any permission
        assert admin_profile.has_permission('any.permission') is True
        assert admin_profile.has_permission('sales.add_sale') is True
    
    def test_user_permission_check(self, user_profile):
        """Test permission checking for non-admin user"""
        # Create a permission
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Zone)
        permission = Permission.objects.create(
            codename='test_permission',
            name='Test Permission',
            content_type=content_type,
        )
        
        # User doesn't have permission yet
        assert user_profile.has_permission('core.test_permission') is False
        
        # Grant permission
        user_profile.user.user_permissions.add(permission)
        # Clear Django's permission cache
        if hasattr(user_profile.user, '_perm_cache'):
            delattr(user_profile.user, '_perm_cache')
        if hasattr(user_profile.user, '_user_perm_cache'):
            delattr(user_profile.user, '_user_perm_cache')
        
        # Now user should have permission
        assert user_profile.has_permission('core.test_permission') is True
    
    def test_get_all_permissions(self, user_profile):
        """Test getting all user permissions"""
        permissions = user_profile.get_all_permissions()
        assert isinstance(permissions, set)


# ============= API Tests =============

@pytest.mark.django_db
@pytest.mark.api
class TestZoneAPI:
    """Test Zone API endpoints"""
    
    def test_list_zones_unauthenticated(self, api_client):
        """Test listing zones without authentication"""
        url = reverse('zone-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_zones_authenticated(self, authenticated_client, zone):
        """Test listing zones with authentication"""
        url = reverse('zone-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_create_zone(self, admin_client):
        """Test creating a zone"""
        url = reverse('zone-list')
        data = {
            'name': 'New Zone',
            'address': '123 New Street',
            'description': 'A new test zone',
            'is_active': True
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Zone'
        
        # Verify in database
        zone = Zone.objects.get(name='New Zone')
        assert zone.address == '123 New Street'
    
    def test_retrieve_zone(self, authenticated_client, zone):
        """Test retrieving a specific zone"""
        url = reverse('zone-detail', kwargs={'pk': zone.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == zone.name
    
    def test_update_zone(self, admin_client, zone):
        """Test updating a zone"""
        url = reverse('zone-detail', kwargs={'pk': zone.id})
        data = {
            'name': 'Updated Zone Name',
            'address': zone.address,
            'description': 'Updated description',
            'is_active': True
        }
        response = admin_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        zone.refresh_from_db()
        assert zone.name == 'Updated Zone Name'
        assert zone.description == 'Updated description'
    
    def test_delete_zone(self, admin_client, db):
        """Test deleting a zone"""
        # Create a zone that's safe to delete
        zone_to_delete = Zone.objects.create(
            name="Zone to Delete",
            address="Delete St"
        )
        url = reverse('zone-detail', kwargs={'pk': zone_to_delete.id})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        assert not Zone.objects.filter(id=zone_to_delete.id).exists()


@pytest.mark.django_db
@pytest.mark.api
class TestUserProfileAPI:
    """Test UserProfile API endpoints"""
    
    def test_list_profiles(self, authenticated_client, user_profile):
        """Test listing user profiles"""
        url = reverse('userprofile-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_retrieve_own_profile(self, authenticated_client, user_profile):
        """Test retrieving own profile"""
        url = reverse('userprofile-detail', kwargs={'pk': user_profile.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['role'] == 'commercial'


@pytest.mark.django_db
@pytest.mark.api
class TestAuthenticationAPI:
    """Test JWT Authentication"""
    
    def test_obtain_token(self, api_client, regular_user):
        """Test obtaining JWT token"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_obtain_token_invalid_credentials(self, api_client, regular_user):
        """Test token with invalid credentials"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, api_client, regular_user):
        """Test refreshing JWT token"""
        # First get tokens
        obtain_url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        obtain_response = api_client.post(obtain_url, data, format='json')
        refresh_token = obtain_response.data['refresh']
        
        # Now refresh
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': refresh_token}
        response = api_client.post(refresh_url, refresh_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_verify_token(self, api_client, regular_user):
        """Test verifying JWT token"""
        # Get token
        obtain_url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        obtain_response = api_client.post(obtain_url, data, format='json')
        access_token = obtain_response.data['access']
        
        # Verify token
        verify_url = reverse('token_verify')
        verify_data = {'token': access_token}
        response = api_client.post(verify_url, verify_data, format='json')
        assert response.status_code == status.HTTP_200_OK


# ============= Integration Tests =============

@pytest.mark.django_db
@pytest.mark.integration
class TestUserProfileIntegration:
    """Integration tests for user profiles with zones and permissions"""
    
    def test_user_can_access_assigned_zone(self, authenticated_client, user_profile, zone):
        """Test that user can access their assigned zone"""
        assert user_profile.zone == zone
        
        url = reverse('zone-detail', kwargs={'pk': zone.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    def test_multiple_users_same_zone(self, db, zone):
        """Test multiple users can be assigned to same zone"""
        user1 = UserFactory(password='pass1')
        user2 = UserFactory(password='pass2')
        
        # Get profiles created by signal and update them
        profile1 = UserProfile.objects.get(user=user1)
        profile1.role = 'commercial'
        profile1.zone = zone
        profile1.save()
        
        profile2 = UserProfile.objects.get(user=user2)
        profile2.role = 'cashier'
        profile2.zone = zone
        profile2.save()
        
        assert profile1.zone == profile2.zone
        assert zone.core_users.count() == 2
