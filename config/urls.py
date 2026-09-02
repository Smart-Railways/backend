from django.contrib import admin
from django.urls import include, path
from .router import router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("railways/", include(router.urls)),
]