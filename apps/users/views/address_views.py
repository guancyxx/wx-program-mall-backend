"""
User address management views with RESTful API design.
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response
from ..models import Address
from ..serializers import AddressSerializer


class AddressViewSet(viewsets.ModelViewSet):
    """
    RESTful API for address management.
    
    Endpoints:
    - GET /users/addresses/ - List all addresses
    - POST /users/addresses/ - Create new address
    - GET /users/addresses/{id}/ - Get address detail
    - PUT /users/addresses/{id}/ - Update address (full)
    - PATCH /users/addresses/{id}/ - Update address (partial)
    - DELETE /users/addresses/{id}/ - Delete address
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return addresses for current user, ordered by default first, then by creation time"""
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
    
    def perform_create(self, serializer):
        """Set user when creating address"""
        serializer.save(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """List addresses with custom response format"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data, 'Address list retrieved successfully')
    
    def create(self, request, *args, **kwargs):
        """Create address with custom response format"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, 'Address created successfully', status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Get address detail with custom response format"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data, 'Address retrieved successfully')
    
    def update(self, request, *args, **kwargs):
        """Update address (full) with custom response format"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data, 'Address updated successfully')
    
    def partial_update(self, request, *args, **kwargs):
        """Update address (partial) with custom response format"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete address with custom response format"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(None, 'Address deleted successfully')
