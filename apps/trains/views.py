from rest_framework import viewsets

from .models import Train, TrainSchedule, TrainMovement
from .serializers import (
    TrainSerializer,
    TrainScheduleSerializer,
    TrainMovementSerializer,
)

from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainMovement
from apps.trains.serializers import TrainOperationsSerializer


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer


class TrainScheduleViewSet(viewsets.ModelViewSet):
    queryset = TrainSchedule.objects.select_related(
        "train",
        "section"
    ).all()

    serializer_class = TrainScheduleSerializer


class TrainMovementViewSet(viewsets.ModelViewSet):
    queryset = TrainMovement.objects.select_related(
        "schedule",
        "schedule__train",
        "schedule__section",
    ).all()

    serializer_class = TrainMovementSerializer

class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer

    @action(detail=False, methods=["get"])
    def operations(self, request):
        service_date = request.query_params.get("date")
        source = request.query_params.get("source")
        destination = request.query_params.get("destination")

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
                {"error": "date must be in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        section = get_object_or_404(
            RailwaySection,
            source_station_code=source.upper(),
            destination_station_code=destination.upper(),
            is_active=True,
        )

        schedules = (
            TrainSchedule.objects
            .filter(
                section=section,
                is_active=True,
            )
            .select_related("train")
        )

        results = []

        for schedule in schedules:

            # Check whether train actually runs on this day
            day_index = service_date.weekday()

            if schedule.running_days[day_index] != "1":
                continue

            movement = (
                TrainMovement.objects
                .filter(
                    schedule=schedule,
                    service_date=service_date,
                )
                .first()
            )

            delay_minutes = None

            if movement:
                if (
                    movement.actual_entry_time
                    and movement.actual_exit_time
                ):
                    scheduled_entry = movement.actual_entry_time.replace(
                        hour=schedule.scheduled_entry_time.hour,
                        minute=schedule.scheduled_entry_time.minute,
                        second=0,
                        microsecond=0,
                    )

                    delay_minutes = int(
                        (
                            movement.actual_entry_time
                            - scheduled_entry
                        ).total_seconds()
                        / 60
                    )

            results.append(
                {
                    "train_number": schedule.train.train_number,
                    "train_name": schedule.train.name,
                    "train_type": schedule.train.train_type,
                    "priority": schedule.train.priority,

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

                    "movement": (
                        {
                            "actual_entry_time": movement.actual_entry_time,
                            "actual_exit_time": movement.actual_exit_time,
                        }
                        if movement
                        else None
                    ),

                    "delay_minutes": delay_minutes,
                }
            )

        serializer = TrainOperationsSerializer(results, many=True)

        return Response(
            {
                "date": service_date,
                "source": source.upper(),
                "destination": destination.upper(),
                "count": len(results),
                "trains": serializer.data,
            }
        )