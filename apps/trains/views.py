from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.corridors.models import RailwaySection

from .models import Train, TrainSchedule, TrainMovement
from .serializers import (
    TrainSerializer,
    TrainScheduleSerializer,
    TrainMovementSerializer,
    TrainOperationsSerializer,
)

class TrainViewSet(viewsets.ModelViewSet):
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
            )[:40]
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


class TrainScheduleViewSet(viewsets.ModelViewSet):
    queryset = (
        TrainSchedule.objects
        .select_related(
            "train",
            "section",
        )
        .all()
    )

    serializer_class = TrainScheduleSerializer


class TrainMovementViewSet(viewsets.ModelViewSet):
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