from django.contrib import admin
from .models import Movie, Screen, Show, Seat, Booking

admin.site.register(Movie)
admin.site.register(Screen)
admin.site.register(Show)
admin.site.register(Seat)
admin.site.register(Booking)
