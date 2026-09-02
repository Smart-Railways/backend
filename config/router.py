from rest_framework.routers import DefaultRouter

from apps.assets.views import AssetViewSet
from apps.blocks.views import BlockWindowViewSet
from apps.corridors.views import RailwaySectionViewSet
from apps.maintenance.views import MaintenanceTaskViewSet
from apps.trains.views import TrainViewSet, TrainMovementViewSet

router = DefaultRouter()

router.register(
    "sections",
    RailwaySectionViewSet,
    basename="section",
)

router.register(
    "assets",
    AssetViewSet,
    basename="asset",
)

router.register(
    "maintenances",
    MaintenanceTaskViewSet,
    basename="maintenance",
)

router.register(
    "trains",
    TrainViewSet,
    basename="train",
)

router.register(
    "train-movements",
    TrainMovementViewSet,
    basename="train-movement",
)

router.register(
    "blocks",
    BlockWindowViewSet,
    basename="block",
)

router.register(
    "block-windows",
    BlockWindowViewSet,
    basename="block-window",
)