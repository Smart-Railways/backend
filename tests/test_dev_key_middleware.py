import unittest
from unittest.mock import MagicMock, patch
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware import DevKeyMiddleware


class TestDevKeyMiddleware(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mock_response = HttpResponse("OK", status=200)
        self.get_response = MagicMock(return_value=self.mock_response)
        self.middleware = DevKeyMiddleware(self.get_response)

    @override_settings(DEBUG=True, DEV_KEY="secret-123")
    def test_debug_missing_key_returns_403(self):
        """When DEBUG=True and X-DEV-KEY is omitted, return 403 Forbidden."""
        request = self.factory.get("/railways/sections/")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)
        self.assertIn("Forbidden", response.content.decode())
        self.get_response.assert_not_called()

    @override_settings(DEBUG=True, DEV_KEY="secret-123")
    def test_debug_invalid_key_returns_403(self):
        """When DEBUG=True and X-DEV-KEY is wrong, return 403 Forbidden."""
        request = self.factory.get("/railways/sections/", HTTP_X_DEV_KEY="wrong-key")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)
        self.get_response.assert_not_called()

    @override_settings(DEBUG=True, DEV_KEY="secret-123")
    def test_debug_valid_key_allows_request(self):
        """When DEBUG=True and valid X-DEV-KEY is supplied, pass request through."""
        request = self.factory.get("/railways/sections/", HTTP_X_DEV_KEY="secret-123")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_once_with(request)

    @override_settings(DEBUG=False, DEV_KEY_REQUIRED=False)
    def test_production_mode_allows_requests_without_key(self):
        """When DEBUG=False, requests pass without requiring X-DEV-KEY."""
        request = self.factory.get("/railways/sections/")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_once_with(request)

    @override_settings(DEBUG=True, DEV_KEY="secret-123")
    def test_cors_options_preflight_exempted(self):
        """CORS preflight OPTIONS requests must pass through without key."""
        request = self.factory.options("/railways/sections/")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_once_with(request)

    @override_settings(DEBUG=True, DEV_KEY="secret-123")
    def test_admin_and_static_exempted(self):
        """Django admin and static assets are exempted from dev key check."""
        for path in ["/admin/", "/admin/login/", "/static/css/base.css", "/favicon.ico"]:
            self.get_response.reset_mock()
            request = self.factory.get(path)
            response = self.middleware(request)

            self.assertEqual(response.status_code, 200)
            self.get_response.assert_called_once_with(request)


if __name__ == "__main__":
    unittest.main()
