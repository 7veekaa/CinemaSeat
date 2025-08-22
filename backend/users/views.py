from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Movie, Show, Seat, Booking
from .serializers import (
    MovieSerializer,
    ShowSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    UserSerializer,
    RegisterSerializer,
)

def health(request):
    return JsonResponse({"status": "ok"})

def ping(request):
    return JsonResponse({"message": "pong"})

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

# ---------- Cinema endpoints ----------

class MovieListView(generics.ListAPIView):
    queryset = Movie.objects.all().order_by("-id")
    serializer_class = MovieSerializer
    permission_classes = [AllowAny]

class ShowListView(generics.ListAPIView):
    serializer_class = ShowSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        movie_id = self.request.query_params.get("movie_id")
        qs = Show.objects.select_related("movie", "screen")
        if movie_id:
            qs = qs.filter(movie_id=movie_id)
        return qs

class SeatsForShowView(generics.ListAPIView):
    """
    Returns seat map with availability for a show.
    GET /api/shows/<id>/seats/
    """
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        show_id = kwargs["pk"]
        show = Show.objects.select_related("screen").get(pk=show_id)

        all_seats = Seat.objects.filter(screen=show.screen).values("id", "row", "col")

        booked_seat_ids = set(
            Seat.objects.filter(
                bookings__show=show, bookings__status__in=["PENDING", "CONFIRMED"]
            ).values_list("id", flat=True)
        )

        data = []
        for s in all_seats:
            s = dict(s)
            s["is_booked"] = s["id"] in booked_seat_ids
            data.append(s)

        return Response({"show_id": show_id, "screen": show.screen.name, "seats": data})

class BookingCreateView(generics.CreateAPIView):
    """
    POST /api/bookings/
    body: {"show_id": <int>, "seat_ids": [int, ...]}
    """
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        show_id = ser.validated_data["show_id"]
        seat_ids = ser.validated_data["seat_ids"]

        show = Show.objects.select_for_update().select_related("screen").get(pk=show_id)

        seats = list(
            Seat.objects.select_for_update().filter(id__in=seat_ids, screen=show.screen)
        )
        if len(seats) != len(seat_ids):
            return Response(
                {"detail": "One or more seats are invalid for this show/screen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_booked = Seat.objects.filter(
            id__in=seat_ids,
            bookings__show=show,
            bookings__status__in=["PENDING", "CONFIRMED"],
        ).exists()
        if already_booked:
            return Response(
                {"detail": "Some seats are already booked."},
                status=status.HTTP_409_CONFLICT,
            )

        total_amount = show.price * len(seats)
        booking = Booking.objects.create(
            user=request.user,
            show=show,
            total_amount=total_amount,
            status=Booking.CONFIRMED,
        )
        booking.seats.set(seats)

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("show__movie", "show__screen")
            .prefetch_related("seats")
        )
