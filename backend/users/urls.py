from django.urls import path
from .views import (
    health, ping,
    RegisterView, MeView,
    MovieListView, ShowListView, SeatsForShowView,
    BookingCreateView, MyBookingsView,
)

urlpatterns = [
    # health & sanity
    path("health/", health, name="health"),
    path("ping/", ping, name="ping"),

    # auth-lite
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),

    # cinema
    path("movies/", MovieListView.as_view(), name="movies"),
    path("shows/", ShowListView.as_view(), name="shows"),
    path("shows/<int:pk>/seats/", SeatsForShowView.as_view(), name="seats-for-show"),
    path("bookings/", BookingCreateView.as_view(), name="booking-create"),
    path("my-bookings/", MyBookingsView.as_view(), name="my-bookings"),
]
