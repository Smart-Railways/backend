import os
import unittest
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory, override_settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import Throttled

from config.throttling import (
    RailwayAnonRateThrottle,
    RailwayUserRateThrottle,
    AIEndpointThrottle,
)


class MockRateView(APIView):
    throttle_classes = [RailwayAnonRateThrottle]

    def get(self, request):
        return Response({"status": "ok"})


class MockAIView(APIView):
    throttle_classes = [AIEndpointThrottle]

    def post(self, request):
        return Response({"status": "ok"})


class TestDRFThrottling(unittest.TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def tearDown(self):
        cache.clear()

    def test_anon_rate_throttle_blocks_excess_requests(self):
        """Verify anonymous requests are throttled once exceeding the rate limit."""
        throttle = RailwayAnonRateThrottle()
        throttle.rate = "3/minute"
        throttle.num_requests, throttle.duration = throttle.parse_rate(throttle.rate)

        request = self.factory.get("/railways/sections/", REMOTE_ADDR="192.168.1.50")
        view = MockRateView()

        # First 3 requests should pass
        for i in range(3):
            self.assertTrue(
                throttle.allow_request(request, view),
                f"Request {i+1} should be allowed",
            )

        # 4th request must be throttled
        self.assertFalse(
            throttle.allow_request(request, view),
            "Request 4 should be throttled (429)",
        )

    def test_ai_endpoint_throttle_blocks_excess_ai_calls(self):
        """Verify AI endpoints enforce dedicated AI rate limiting."""
        throttle = AIEndpointThrottle()
        throttle.rate = "2/minute"
        throttle.num_requests, throttle.duration = throttle.parse_rate(throttle.rate)

        request = self.factory.post(
            "/railways/block-windows/recommendation/",
            REMOTE_ADDR="192.168.1.60",
        )
        view = MockAIView()

        # First 2 requests pass
        self.assertTrue(throttle.allow_request(request, view))
        self.assertTrue(throttle.allow_request(request, view))

        # 3rd request must be blocked
        self.assertFalse(throttle.allow_request(request, view))

    @override_settings(DEV_KEY="my-secret-key")
    def test_dev_key_bypass_throttle_when_enabled(self):
        """Verify DEV_KEY_BYPASS_THROTTLE allows trusted dev key to bypass rate limits."""
        throttle = RailwayAnonRateThrottle()
        throttle.rate = "1/minute"
        throttle.num_requests, throttle.duration = throttle.parse_rate(throttle.rate)

        request = self.factory.get(
            "/railways/sections/",
            REMOTE_ADDR="192.168.1.70",
            HTTP_X_DEV_KEY="my-secret-key",
        )
        view = MockRateView()

        # With bypass enabled in environment
        with unittest.mock.patch.dict(os.environ, {"DEV_KEY_BYPASS_THROTTLE": "true"}):
            self.assertTrue(throttle.allow_request(request, view))
            self.assertTrue(throttle.allow_request(request, view))
            self.assertTrue(throttle.allow_request(request, view))


if __name__ == "__main__":
    unittest.main()
