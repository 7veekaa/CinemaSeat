from django.urls import path
from .views import health, ping

urlpatterns = [
    path("health/", health),
    path("ping/", ping),
]
