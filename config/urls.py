from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse, HttpResponse
from django.db import connection
from .router import router


def root_view(request):
    return JsonResponse({
        "service": "Railway-AI Unified Backend API",
        "version": "1.0.0",
        "status": "online",
        "message": "Railway-AI Backend is active and running.",
        "endpoints": {
            "api_root": "/railways/",
            "health": "/health/",
            "ready": "/ready/",
            "admin": "/admin/",
        },
        "features": {
            "embedded_ai_engine": True,
            "constraint_solver": "Google OR-Tools CP-SAT",
            "failure_predictor": "Calibrated XGBoost",
        }
    })


def favicon_view(request):
    return HttpResponse(status=204)


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "railway-backend",
        "version": "1.0.0"
    })


def ready_check(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    ai_ok = False
    try:
        from apps.blocks.ai_client import RailwayAIClient
        ai_ok = RailwayAIClient.is_healthy()
    except Exception:
        pass

    status_code = 200 if db_ok else 503
    return JsonResponse({
        "status": "ready" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "ai_service": "online" if ai_ok else "offline"
    }, status=status_code)


urlpatterns = [
    path("", root_view, name="root"),
    path("favicon.ico", favicon_view, name="favicon"),
    path("health/", health_check, name="health"),
    path("ready/", ready_check, name="ready"),
    path("railways/health/", health_check, name="railways-health"),
    path("railways/ready/", ready_check, name="railways-ready"),
    path("admin/", admin.site.urls),
    path("railways/", include(router.urls)),
]

