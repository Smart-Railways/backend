from rest_framework.viewsets import ModelViewSet

from .models import BlockWindow
from .serializers import BlockWindowSerializer


class BlockWindowViewSet(ModelViewSet):
    queryset = BlockWindow.objects.select_related("section").all()
    serializer_class = BlockWindowSerializer
