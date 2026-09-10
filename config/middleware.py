import hmac
from django.conf import settings
from django.http import JsonResponse


class DevKeyMiddleware:
    """
    Middleware that enforces an 'X-DEV-KEY' header check when DEBUG=True
    (or when DEV_KEY_REQUIRED=True), preventing unauthorized spam or access
    to the API during development and staging.
    """

    EXEMPT_PATHS = (
        "/admin/",
        "/static/",
        "/media/",
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_debug = getattr(settings, "DEBUG", False)
        dev_key_required = getattr(settings, "DEV_KEY_REQUIRED", False)

        # Enforce when DEBUG=True or when DEV_KEY_REQUIRED=True
        if is_debug or dev_key_required:
            # Exempt CORS preflight OPTIONS requests
            if request.method == "OPTIONS":
                return self.get_response(request)

            # Exempt browser admin, static assets, and favicon
            path = request.path
            if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
                return self.get_response(request)

            expected_key = getattr(
                settings,
                "DEV_KEY",
                "",
            )

            # Retrieve X-DEV-KEY from request headers (Django 2.2+ request.headers or META)
            provided_key = (
                request.headers.get("X-DEV-KEY")
                or request.headers.get("x-dev-key")
                or request.META.get("HTTP_X_DEV_KEY")
            )

            if not provided_key or not hmac.compare_digest(str(provided_key), str(expected_key)):
                return JsonResponse(
                    {
                        "error": "Forbidden: Missing or invalid X-DEV-KEY header.",
                        "detail": "Access to this API is restricted during development without a development key.",
                    },
                    status=403,
                )

        return self.get_response(request)
