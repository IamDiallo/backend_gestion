from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission
from .models import UserProfile, Zone


class PermissionSerializer(serializers.ModelSerializer):
    content_type_name = serializers.CharField(source='content_type.name', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'content_type_name', 'app_label']


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name', 'address', 'description', 'is_active']


class UserProfileSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['id', 'role', 'zone', 'zone_name', 'is_active',
                  'user_username', 'user_email', 'user_full_name']

    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        extra_kwargs = {'password': {'write_only': True}}


class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']
        
    def create(self, validated_data):
        permission_ids = self.initial_data.get('permissions', [])
        group = Group.objects.create(name=validated_data.get('name', ''))
        
        if permission_ids:
            permission_ids = [int(id) if isinstance(id, str) and id.isdigit() else id for id in permission_ids]
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)
        
        return group
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        
        permission_ids = self.initial_data.get('permissions', [])
        if permission_ids is not None:
            permission_ids = [int(id) if isinstance(id, str) and id.isdigit() else id for id in permission_ids]
            permissions = Permission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)
            
        return instance


class UserSerializer(serializers.ModelSerializer):
    profile_data = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    role = serializers.CharField(write_only=True, required=False, allow_null=True)
    zone = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_profile_active = serializers.BooleanField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 
                  'is_staff', 'profile_data', 'permissions', 'groups', 
                  'role', 'zone', 'is_profile_active']
        read_only_fields = ['id']
        
    def get_profile_data(self, obj):
        try:
            profile = obj.profile
            if not profile:
                return None
                
            return {
                'id': profile.id,
                'role': profile.role,
                'zone': profile.zone.id if profile.zone else None,
                'zone_name': profile.zone.name if profile.zone else None,
                'is_active': profile.is_active
            }
        except Exception:
            return None
    
    def get_permissions(self, obj):
        try:
            if not hasattr(obj, 'profile'):
                return []
            return list(obj.profile.get_all_permissions())
        except Exception:
            return []
    
    def get_groups(self, obj):
        try:
            django_groups = obj.groups.all()
            return [{'id': group.id, 'name': group.name} for group in django_groups]
        except Exception:
            return []

    def create(self, validated_data):
        role = validated_data.pop('role', None)
        zone_id = validated_data.pop('zone', None)
        is_profile_active = validated_data.pop('is_profile_active', True)
        
        user = User.objects.create(**validated_data)
        
        if role or zone_id:
            UserProfile.objects.create(
                user=user,
                role=role or 'user',
                zone_id=zone_id,
                is_active=is_profile_active
            )
        
        return user
    
    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        zone_id = validated_data.pop('zone', None)
        is_profile_active = validated_data.pop('is_profile_active', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if hasattr(instance, 'profile'):
            profile = instance.profile
            if role is not None:
                profile.role = role
            if zone_id is not None:
                profile.zone_id = zone_id
            if is_profile_active is not None:
                profile.is_active = is_profile_active
            profile.save()
        elif role or zone_id:
            UserProfile.objects.create(
                user=instance,
                role=role or 'user',
                zone_id=zone_id,
                is_active=is_profile_active if is_profile_active is not None else True
            )
        
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        return attrs
