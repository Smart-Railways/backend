from rest_framework.routers import DefaultRouter

from apps.assets.views import AssetViewSet
from apps.blocks.views import BlockWindowViewSet
from apps.corridors.views import RailwaySectionViewSet
from apps.maintenance.views import MaintenanceTaskViewSet
from apps.trains.views import (
    TrainViewSet,
    TrainScheduleViewSet,
    TrainMovementViewSet,
)


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
    "maintenance-tasks",
    MaintenanceTaskViewSet,
    basename="maintenance-task",
)

# router.register(
#     "plans",
#     MaintenancePlanViewSet,
#     basename="plan",
# )

router.register(
    "trains",
    TrainViewSet,
    basename="train",
)

router.register(
    "train-schedules",
    TrainScheduleViewSet,
    basename="train-schedule",
)

router.register(
    "train-movements",
    TrainMovementViewSet,
    basename="train-movement",
)

router.register(
    "block-windows",
    BlockWindowViewSet,
    basename="block-window",
)