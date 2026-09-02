from rest_framework.viewsets import ModelViewSet

from .models import Asset
from .serializers import AssetSerializer


class AssetViewSet(ModelViewSet):
    queryset = Asset.objects.select_related("section").all()
    serializer_class = AssetSerializer