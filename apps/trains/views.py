from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.db.models.functions import Substr
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.corridors.models import RailwaySection

from .models import Train, TrainSchedule, TrainMovement
from .pagination import TrainSchedulePagination
from .serializers import (
    TrainSerializer,
    TrainScheduleSerializer,
    TrainMovementSerializer,
    TrainOperationsSerializer,
)

class TrainViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer

    @action(detail=False, methods=["get"])
    def operations(self, request):
        service_date = request.query_params.get("date")
        source = request.query_params.get("source")
        destination = request.query_params.get("destination")

        # -------------------------------------------------
        # Validate query parameters
        # -------------------------------------------------

        if not service_date or not source or not destination:
            return Response(
                {
                    "error": "date, source and destination are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service_date = date.fromisoformat(service_date)
        except ValueError:
            return Response(
                {
                    "error": "date must be in YYYY-MM-DD format."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Find railway section
        # -------------------------------------------------

        section = get_object_or_404(
            RailwaySection,
            source_station_code=source.upper(),
            destination_station_code=destination.upper(),
            is_active=True,
        )

        # -------------------------------------------------
        # Get ONLY tracked trains
        #
        # TrainMovement exists only when the train has
        # actually been live-synced.
        # -------------------------------------------------

        movements = (
            TrainMovement.objects
            .filter(
                schedule__section=section,
                service_date=service_date,
            )
            .select_related(
                "schedule",
                "schedule__train",
                "schedule__section",
            )
            .order_by(
                "schedule__scheduled_entry_time"
            )[:30]
        )

        results = []

        IST = ZoneInfo("Asia/Kolkata")

        for movement in movements:

            schedule = movement.schedule
            train = schedule.train

            # -------------------------------------------------
            # Calculate entry delay
            # -------------------------------------------------

            delay_minutes = None

            if movement.actual_entry_time:

                scheduled_entry = datetime.combine(
                    service_date,
                    schedule.scheduled_entry_time,
                )

                scheduled_entry = scheduled_entry.replace(
                    tzinfo=IST
                )

                delay_minutes = int(
                    (
                        movement.actual_entry_time
                        - scheduled_entry
                    ).total_seconds()
                    / 60
                )

            # -------------------------------------------------
            # Build response
            # -------------------------------------------------

            results.append(
                {
                    "train_number": train.train_number,
                    "train_name": train.name,
                    "train_type": train.train_type,
                    "priority": train.priority,

                    "section": {
                        "name": section.name,
                        "source": section.source_station,
                        "source_code": section.source_station_code,
                        "destination": section.destination_station,
                        "destination_code": section.destination_station_code,
                    },

                    "schedule": {
                        "entry_time": schedule.scheduled_entry_time,
                        "exit_time": schedule.scheduled_exit_time,
                    },

                    "movement": {
                        "actual_entry_time": (
                            movement.actual_entry_time
                        ),
                        "actual_exit_time": (
                            movement.actual_exit_time
                        ),
                    },

                    "delay_minutes": delay_minutes,
                }
            )

        serializer = TrainOperationsSerializer(
            results,
            many=True,
        )

        return Response(
            {
                "date": service_date,
                "source": source.upper(),
                "destination": destination.upper(),
                "count": len(results),
                "trains": serializer.data,
            }
        )


class TrainScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        TrainSchedule.objects
        .select_related(
            "train",
            "section",
        )
        .order_by("scheduled_entry_time", "id")
    )
    serializer_class = TrainScheduleSerializer
    pagination_class = TrainSchedulePagination

    def get_queryset(self):
        queryset = super().get_queryset()

        date_param = self.request.query_params.get("date")
        source = (
            self.request.query_params.get("source")
            or self.request.query_params.get("src")
            or self.request.query_params.get("source_station")
            or self.request.query_params.get("src_station")
        )
        destination = (
            self.request.query_params.get("destination")
            or self.request.query_params.get("dest")
            or self.request.query_params.get("dst")
            or self.request.query_params.get("destination_station")
            or self.request.query_params.get("dest_station")
        )

        if date_param:
            try:
                parsed_date = date.fromisoformat(date_param.strip())
            except ValueError:
                raise ValidationError(
                    {"date": "date must be in YYYY-MM-DD format."}
                )

            # Monday = 0, Sunday = 6; running_days is a 7-character string indexed 0 to 6
            day_index = parsed_date.weekday()
            queryset = queryset.annotate(
                day_running=Substr("running_days", day_index + 1, 1)
            ).filter(day_running="1")

        if source:
            source = source.strip()
            queryset = queryset.filter(
                Q(section__source_station_code__iexact=source)
                | Q(section__source_station__icontains=source)
            )

        if destination:
            destination = destination.strip()
            queryset = queryset.filter(
                Q(section__destination_station_code__iexact=destination)
                | Q(section__destination_station__icontains=destination)
            )

        return queryset


class TrainMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        TrainMovement.objects
        .select_related(
            "schedule",
            "schedule__train",
            "schedule__section",
        )
        .all()
    )

    serializer_class = TrainMovementSerializer