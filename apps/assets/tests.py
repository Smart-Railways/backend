from rest_framework import status
from rest_framework.test import APITestCase

from apps.corridors.models import RailwaySection

from .models import Asset


class AssetPaginationAPITest(APITestCase):
    def setUp(self):
        self.section = RailwaySection.objects.create(
            name="Delhi - Agra",
            source_station="New Delhi",
            source_station_code="NDLS",
            destination_station="Agra Cantt",
            destination_station_code="AGC",
            distance_km=195,
        )
        Asset.objects.create(
            section=self.section,
            name="Older asset",
            asset_type="SIGNAL",
            department=Asset.Department.SNT,
            criticality=2,
        )
        self.newest_asset = Asset.objects.create(
            section=self.section,
            name="Newest asset",
            asset_type="TRACK_CIRCUIT",
            department=Asset.Department.SNT,
            criticality=4,
        )

    def test_assets_are_paginated_and_newest_first(self):
        response = self.client.get("/railways/assets/?page=1&page_size=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(response.data["results"][0]["id"], self.newest_asset.id)
