from datetime import date, time
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.corridors.models import RailwaySection
from apps.trains.models import Train, TrainMovement, TrainSchedule
from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.train_selection import get_relevant_train_numbers


class TrainScheduleViewSetTestCase(APITestCase):
    def setUp(self):
        self.section_delhi_kanpur = RailwaySection.objects.create(
            name="Delhi - Kanpur Corridor",
            source_station="New Delhi",
            source_station_code="NDLS",
            destination_station="Kanpur Central",
            destination_station_code="CNB",
            distance_km=440.0,
            is_active=True,
        )
        self.section_mumbai_surat = RailwaySection.objects.create(
            name="Mumbai - Surat Corridor",
            source_station="Mumbai Central",
            source_station_code="MMCT",
            destination_station="Surat",
            destination_station_code="ST",
            distance_km=263.0,
            is_active=True,
        )

        self.train_1 = Train.objects.create(
            train_number="12001",
            name="Shatabdi Express",
            train_type=Train.TrainType.SHATABDI,
            priority=8,
        )
        self.train_2 = Train.objects.create(
            train_number="22436",
            name="Vande Bharat Express",
            train_type=Train.TrainType.VB,
            priority=9,
        )
        self.train_3 = Train.objects.create(
            train_number="12951",
            name="Mumbai Rajdhani",
            train_type=Train.TrainType.RAJDHANI,
            priority=9,
        )

        # Schedule 1: Delhi -> Kanpur, runs Monday to Friday (1111100)
        self.sched_1 = TrainSchedule.objects.create(
            train=self.train_1,
            section=self.section_delhi_kanpur,
            scheduled_entry_time="06:00:00",
            scheduled_exit_time="11:00:00",
            running_days="1111100",
            is_active=True,
        )
        # Schedule 2: Delhi -> Kanpur, runs Weekends only (0000011)
        self.sched_2 = TrainSchedule.objects.create(
            train=self.train_2,
            section=self.section_delhi_kanpur,
            scheduled_entry_time="07:00:00",
            scheduled_exit_time="12:00:00",
            running_days="0000011",
            is_active=True,
        )
        # Schedule 3: Mumbai -> Surat, runs daily (1111111)
        self.sched_3 = TrainSchedule.objects.create(
            train=self.train_3,
            section=self.section_mumbai_surat,
            scheduled_entry_time="16:00:00",
            scheduled_exit_time="19:30:00",
            running_days="1111111",
            is_active=True,
        )

    def test_list_schedules_without_params(self):
        """Endpoint without params returns paginated envelope with all schedules."""
        url = "/railways/train-schedules/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

    def test_pagination_page_size(self):
        """Pagination respects page_size query parameter."""
        url = "/railways/train-schedules/?page_size=2"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])

    def test_filter_by_date_weekday_and_weekend(self):
        """Filter by date returns only trains that run on that specific day of the week."""
        # 2026-09-07 is Monday (day_index = 0)
        response_monday = self.client.get("/railways/train-schedules/?date=2026-09-07")
        self.assertEqual(response_monday.status_code, status.HTTP_200_OK)
        ids_monday = [item["id"] for item in response_monday.data["results"]]
        # sched_1 (runs Mon-Fri) and sched_3 (runs daily) should match, sched_2 (weekends only) should not
        self.assertIn(self.sched_1.id, ids_monday)
        self.assertIn(self.sched_3.id, ids_monday)
        self.assertNotIn(self.sched_2.id, ids_monday)

        # 2026-09-06 is Sunday (day_index = 6)
        response_sunday = self.client.get("/railways/train-schedules/?date=2026-09-06")
        self.assertEqual(response_sunday.status_code, status.HTTP_200_OK)
        ids_sunday = [item["id"] for item in response_sunday.data["results"]]
        # sched_2 (runs weekends) and sched_3 (runs daily) should match, sched_1 (Mon-Fri) should not
        self.assertIn(self.sched_2.id, ids_sunday)
        self.assertIn(self.sched_3.id, ids_sunday)
        self.assertNotIn(self.sched_1.id, ids_sunday)

    def test_filter_by_date_invalid_format(self):
        """Invalid date format returns 400 Bad Request."""
        response = self.client.get("/railways/train-schedules/?date=2026/09/07")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_filter_by_source_station_code_and_name(self):
        """Filter by source station code (exact/case-insensitive) and station name."""
        # By code using ?source=
        res_code = self.client.get("/railways/train-schedules/?source=NDLS")
        self.assertEqual(res_code.status_code, status.HTTP_200_OK)
        self.assertEqual(res_code.data["count"], 2)

        # By code using ?src= (lowercase)
        res_code_lower = self.client.get("/railways/train-schedules/?src=ndls")
        self.assertEqual(res_code_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(res_code_lower.data["count"], 2)

        # By partial name
        res_name = self.client.get("/railways/train-schedules/?src=Delhi")
        self.assertEqual(res_name.status_code, status.HTTP_200_OK)
        self.assertEqual(res_name.data["count"], 2)

        # Mumbai
        res_mumbai = self.client.get("/railways/train-schedules/?source=MMCT")
        self.assertEqual(res_mumbai.status_code, status.HTTP_200_OK)
        self.assertEqual(res_mumbai.data["count"], 1)
        self.assertEqual(res_mumbai.data["results"][0]["id"], self.sched_3.id)

    def test_filter_by_destination_station_code_and_name(self):
        """Filter by destination station code and name."""
        # By code using ?dest=
        res_dest_code = self.client.get("/railways/train-schedules/?dest=cnb")
        self.assertEqual(res_dest_code.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dest_code.data["count"], 2)

        # By name using ?destination=
        res_dest_name = self.client.get("/railways/train-schedules/?destination=Surat")
        self.assertEqual(res_dest_name.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dest_name.data["count"], 1)
        self.assertEqual(res_dest_name.data["results"][0]["id"], self.sched_3.id)

    def test_filter_combined_params(self):
        """Filter with date, source station, and destination station together."""
        # Sunday 2026-09-06, source NDLS, destination CNB -> only sched_2
        res = self.client.get("/railways/train-schedules/?date=2026-09-06&src=NDLS&destination=CNB")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], self.sched_2.id)

        # Monday 2026-09-07, source NDLS, destination CNB -> only sched_1
        res2 = self.client.get("/railways/train-schedules/?date=2026-09-07&source=NDLS&dest=CNB")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["count"], 1)
        self.assertEqual(res2.data["results"][0]["id"], self.sched_1.id)

        # Sunday 2026-09-06, source MMCT, destination CNB -> 0 results
        res_none = self.client.get("/railways/train-schedules/?date=2026-09-06&src=MMCT&dest=CNB")
        self.assertEqual(res_none.status_code, status.HTTP_200_OK)
        self.assertEqual(res_none.data["count"], 0)

    def test_retrieve_single_schedule(self):
        """Retrieve by ID returns unpaginated single object."""
        res = self.client.get(f"/railways/train-schedules/{self.sched_1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.sched_1.id)
        self.assertEqual(res.data["train_name"], self.train_1.name)


class LiveTrainSyncTestCase(APITestCase):
    def setUp(self):
        self.section = RailwaySection.objects.create(
            name="Overnight section",
            source_station="Source",
            source_station_code="SRC",
            destination_station="Destination",
            destination_station_code="DST",
            distance_km=100,
            is_active=True,
        )
        self.train = Train.objects.create(
            train_number="22436",
            name="Vande Bharat Express",
            train_type=Train.TrainType.VB,
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            section=self.section,
            scheduled_entry_time=time(23, 30),
            scheduled_exit_time=time(1, 15),
            scheduled_exit_day_offset=1,
            running_days="1111111",
        )

    @patch("apps.trains.services.live_sync.RailKitClient.get_train")
    def test_sync_uses_schedule_and_keeps_actual_times_untouched(self, get_train):
        get_train.return_value = {
            "trainNumber": "22436",
            "trainName": "VANDE BHARAT EX",
            "status": {"delayMinutes": 20, "label": "+20 min delay"},
            # These stations intentionally do not match section boundaries.
            "route": [{"stationCode": "OTHER"}],
        }
        result = sync_live_train("22436", date(2026, 9, 21))

        movement = TrainMovement.objects.get(schedule=self.schedule)
        self.assertEqual(result["updated_movements"][0]["section"], self.section.name)
        self.assertEqual(
            timezone.localtime(movement.estimated_entry_time).time(), time(23, 50)
        )
        self.assertEqual(
            timezone.localtime(movement.estimated_exit_time).time(), time(1, 35)
        )
        self.assertEqual(movement.estimated_exit_time.date(), date(2026, 9, 22))
        self.assertIsNone(movement.actual_entry_time)
        self.assertIsNone(movement.actual_exit_time)

    @patch("apps.trains.services.live_sync.RailKitClient.get_train")
    def test_unknown_delay_does_not_assume_on_time(self, get_train):
        get_train.return_value = {
            "trainNumber": "22436",
            "status": {"delayMinutes": None, "label": "Delay unavailable"},
        }
        result = sync_live_train("22436", date(2026, 9, 21))

        self.assertEqual(result["skipped"], "UNKNOWN_LIVE_STATUS")
        self.assertFalse(TrainMovement.objects.filter(schedule=self.schedule).exists())


class TrainSelectionTestCase(APITestCase):
    def test_selects_30_per_section_with_priority_services_reserved_first(self):
        section = RailwaySection.objects.create(
            name="Selection section",
            source_station="Source",
            source_station_code="SRC",
            destination_station="Destination",
            destination_station_code="DST",
            distance_km=100,
            is_active=True,
        )
        for index in range(35):
            train = Train.objects.create(
                train_number=f"9{index:03d}",
                name=f"Train {index}",
                train_type=Train.TrainType.EXPRESS,
                priority=9 if index < 12 else 5,
            )
            TrainSchedule.objects.create(
                train=train,
                section=section,
                scheduled_entry_time=time(6, 0),
                scheduled_exit_time=time(7, 0),
                running_days="1111111",
            )

        selected = get_relevant_train_numbers(date(2026, 9, 21))

        self.assertEqual(len(selected), 30)
        # The first ten high-priority services are reserved before regulars.
        self.assertTrue({f"9{index:03d}" for index in range(10)}.issubset(selected))
