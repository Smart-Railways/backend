from rest_framework.viewsets import ModelViewSet

from .models import Asset
from .pagination import AssetPagination
from .serializers import AssetSerializer


class AssetViewSet(ModelViewSet):
    queryset = Asset.objects.select_related("section").all().order_by("-id")
    serializer_class = AssetSerializer
    pagination_class = AssetPagination
