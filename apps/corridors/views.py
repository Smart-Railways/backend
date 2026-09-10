from rest_framework.viewsets import ModelViewSet

from .models import RailwaySection
from .serializers import RailwaySectionSerializer

class RailwaySectionViewSet(ModelViewSet):
    queryset = RailwaySection.objects.all().order_by("id")
    serializer_class = RailwaySectionSerializer