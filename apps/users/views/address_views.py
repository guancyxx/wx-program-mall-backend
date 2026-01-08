"""
User address management views.
"""
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.utils import success_response, error_response
from ..models import Address
from ..serializers import AddressSerializer


class AddressViewSet(viewsets.ModelViewSet):
    """Address management viewset"""
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddAddressView(APIView):
    """Add address endpoint matching Node.js API"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return success_response(serializer.data, 'Address added successfully')
        return error_response('Failed to add address', serializer.errors)


class DeleteAddressView(APIView):
    """Delete address endpoint matching Node.js API"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        address_id = request.data.get('id')
        if not address_id:
            return error_response('Address ID is required')

        try:
            address = Address.objects.get(id=address_id, user=request.user)
            address.delete()
            return success_response(None, 'Address deleted successfully')
        except Address.DoesNotExist:
            return error_response('Address not found')


class AddressListView(APIView):
    """Get address list endpoint matching Node.js API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        serializer = AddressSerializer(addresses, many=True)
        return success_response(serializer.data, 'Address list retrieved successfully')

