from django.urls import path
from .views import (
    health, ping, register, me,
    MovieListView, ShowListView, SeatsForShowView,
    BookingCreateView, MyBookingsView
)

urlpatterns = [
    path("health/", health),
    path("ping/", ping),
    path("auth/register/", register),
    path("auth/me/", me),
    path("movies/", MovieListView.as_view()),
    path("shows/", ShowListView.as_view()),
    path("shows/<int:pk>/seats/", SeatsForShowView.as_view()),
    path("bookings/", BookingCreateView.as_view()),
    path("bookings/me/", MyBookingsView.as_view()),
]
