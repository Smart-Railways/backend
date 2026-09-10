import os
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle


class RailwayAnonRateThrottle(AnonRateThrottle):
    """
    IP-based rate throttle for unauthenticated requests.
    Prevents public API spam and scraping bursts.
    """
    scope = "anon"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }

    def allow_request(self, request, view):
        if os.getenv("DEV_KEY_BYPASS_THROTTLE", "False").lower() in ("true", "1", "yes"):
            dev_key = getattr(settings, "DEV_KEY", None)
            provided_key = (
                request.headers.get("X-DEV-KEY")
                or request.headers.get("x-dev-key")
                or request.META.get("HTTP_X_DEV_KEY")
            )
            if dev_key and provided_key and str(dev_key) == str(provided_key):
                return True
        return super().allow_request(request, view)


class RailwayUserRateThrottle(UserRateThrottle):
    """
    User/client-based rate throttle for authenticated requests.
    """
    scope = "user"


class AIEndpointThrottle(AnonRateThrottle):
    """
    Dedicated rate limit for computationally intensive endpoints
    (CP-SAT constraint optimizer, feasible window calculations,
    and live traffic conflict checks).
    Throttles both unauthenticated (by IP) and authenticated (by user ID) clients.
    """
    scope = "ai"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            ident = f"user_{user.pk}"
        else:
            ident = f"ip_{self.get_ident(request)}"

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }

    def allow_request(self, request, view):
        if os.getenv("DEV_KEY_BYPASS_THROTTLE", "False").lower() in ("true", "1", "yes"):
            dev_key = getattr(settings, "DEV_KEY", None)
            provided_key = (
                request.headers.get("X-DEV-KEY")
                or request.headers.get("x-dev-key")
                or request.META.get("HTTP_X_DEV_KEY")
            )
            if dev_key and provided_key and str(dev_key) == str(provided_key):
                return True
        return super().allow_request(request, view)
