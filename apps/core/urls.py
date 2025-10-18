from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'user-profiles', views.UserProfileViewSet, basename='userprofile')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'zones', views.ZoneViewSet, basename='zone')
router.register(r'groups', views.GroupViewSet, basename='group')
router.register(r'permissions', views.PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]
