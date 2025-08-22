from django.urls import path
from cinema.views import health, ping, register, me

urlpatterns = [
    path("health/", health, name="health"),
    path("ping/", ping, name="ping"),
    path("register/", register, name="register"),
    path("me/", me, name="me"),
]
