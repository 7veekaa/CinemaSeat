from django.urls import path
from .views import (
    health, ping,
    MovieListView, ShowListView, SeatsForShowView,
    BookingCreateView, MyBookingsView,
)

urlpatterns = [

    path("health/", health, name="cinema-health"),
    path("ping/", ping, name="cinema-ping"),


    path("movies/", MovieListView.as_view(), name="movies"),                        
    path("movies/<int:pk>/shows/", ShowListView.as_view(), name="movie-shows"),     
    path("shows/<int:pk>/seats/", SeatsForShowView.as_view(), name="seats-for-show"),
    path("bookings/", BookingCreateView.as_view(), name="booking-create"),         
    path("my-bookings/", MyBookingsView.as_view(), name="my-bookings"),             
]
