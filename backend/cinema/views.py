# backend/cinema/views.py
from __future__ import annotations

import json
import os

from django.apps import apps
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated


# -------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------
def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None

def ok(data, code=status.HTTP_200_OK):
    return Response(data, status=code)

# file used for demo persistence if DB save is not possible
DEMO_BOOK_PATH = os.path.join(settings.BASE_DIR, "demo_bookings.json")

def _demo_read():
    try:
        with open(DEMO_BOOK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _demo_write(entries):
    try:
        with open(DEMO_BOOK_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f)
    except Exception:
        pass


# -------------------------------------------------------------------
# simple health
# -------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return ok({"status": "ok", "service": "cinema"})

@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return ok({"pong": True, "now": timezone.now()})


# -------------------------------------------------------------------
# movies
# -------------------------------------------------------------------
class MovieListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        Movie = _get_model("cinema", "Movie")
        data = []
        if Movie:
            try:
                for m in Movie.objects.all():
                    data.append({
                        "id": m.id,
                        "title": getattr(m, "title", getattr(m, "name", f"Movie {m.id}")),
                        "language": getattr(m, "language", ""),
                        "certificate": getattr(m, "certificate", ""),
                        "poster_url": getattr(m, "poster_url", "") or f"https://picsum.photos/seed/{m.id}-poster/300/420",

                    })
            except Exception:
                pass

        if not data:
            data = [
                {"id": 1, "title": "Demo Movie 1", "language": "EN", "certificate": "U/A", "poster_url": ""},
                {"id": 2, "title": "Demo Movie 2", "language": "HI", "certificate": "U/A", "poster_url": ""},
            ]
        return ok(data)


# -------------------------------------------------------------------
# shows for a movie
# -------------------------------------------------------------------
class ShowListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        Show = _get_model("cinema", "Show")
        data = []
        if Show:
            try:
                qs = Show.objects.filter(movie_id=pk).order_by("start_time")
                for s in qs:
                    data.append({
                        "id": s.id,
                        "start_time": getattr(s, "start_time", None),
                    })
            except Exception:
                pass

        if not data:
            data = [
                {"id": 101, "start_time": timezone.now()},
                {"id": 102, "start_time": timezone.now() + timezone.timedelta(hours=3)},
            ]
        return ok(data)


# -------------------------------------------------------------------
# seats for a show (reads DB + demo file, so availability is consistent)
# -------------------------------------------------------------------
class SeatsForShowView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        # default layout: 1..100
        seats = [{"number": str(i), "available": True} for i in range(1, 101)]

        # mark DB bookings as unavailable
        Booking = _get_model("cinema", "Booking")
        if Booking:
            try:
                fields = {f.name for f in Booking._meta.get_fields()}
                taken = set()

                if "seat_number" in fields:
                    taken = {str(n) for n in Booking.objects.filter(show_id=pk)
                                             .values_list("seat_number", flat=True)}
                elif "seat" in fields:
                    # fall back to seat FK -> seat.number if present
                    for b in Booking.objects.filter(show_id=pk).select_related("seat"):
                        n = getattr(getattr(b, "seat", None), "number", None)
                        if n is not None:
                            taken.add(str(n))

                if taken:
                    for s in seats:
                        if s["number"] in taken:
                            s["available"] = False
            except Exception:
                pass

        # mark demo-file bookings as unavailable
        for e in _demo_read():
            if str(e.get("show_id")) == str(pk):
                for s in seats:
                    if s["number"] == str(e.get("seat_number")):
                        s["available"] = False

        return ok(seats)


# -------------------------------------------------------------------
# create booking (DB first, file fallback) — returns 201 or 409
# -------------------------------------------------------------------
class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        show_id = request.data.get("show_id")
        seat_number = request.data.get("seat_number")

        if show_id in (None, "") or seat_number in (None, ""):
            return Response({"detail": "show_id & seat_number required"}, status=400)

        try:
            show_id = int(show_id)
        except Exception:
            return Response({"detail": "show_id must be integer"}, status=400)
        seat_number_str = str(seat_number)

        # try real DB first
        Booking = _get_model("cinema", "Booking")
        if Booking:
            try:
                fields = {f.name for f in Booking._meta.get_fields()}

                # conflict check
                if "seat_number" in fields:
                    if Booking.objects.filter(show_id=show_id, seat_number=seat_number_str).exists():
                        return Response({"detail": "Seat already booked"}, status=409)
                else:
                    # less strict conflict if no seat_number column
                    if Booking.objects.filter(show_id=show_id).exists():
                        pass  # allow create; schema may be different

                create_kwargs = {}
                if "user" in fields:
                    create_kwargs["user"] = request.user
                if "show" in fields or "show_id" in fields:
                    create_kwargs["show_id"] = show_id
                if "seat_number" in fields:
                    create_kwargs["seat_number"] = seat_number_str

                b = Booking.objects.create(**create_kwargs)
                return ok(
                    {"id": getattr(b, "id", 0), "show_id": show_id, "seat_number": seat_number_str},
                    code=status.HTTP_201_CREATED
                )
            except Exception:
                # fall through to file persistence
                pass

        # file fallback (always persists for the demo)
        entries = _demo_read()
        for e in entries:
            if str(e.get("show_id")) == str(show_id) and str(e.get("seat_number")) == seat_number_str:
                return Response({"detail": "Seat already booked"}, status=409)

        new_id = (entries[-1]["id"] + 1) if entries else 1
        entry = {
            "id": new_id,
            "user": request.user.username,
            "show_id": show_id,
            "seat_number": seat_number_str,
            "created_at": timezone.now().isoformat(),
        }
        entries.append(entry)
        _demo_write(entries)
        return ok(entry, code=status.HTTP_201_CREATED)


# -------------------------------------------------------------------
# my bookings (reads DB if possible, else demo file)
# -------------------------------------------------------------------
# ---- My bookings: include movie title + show time when available ----
class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        username = request.user.username

        Booking = _get_model("cinema", "Booking")
        Show = _get_model("cinema", "Show")
        Movie = _get_model("cinema", "Movie")

        # DB path (preferred)
        if Booking:
            try:
                fields = {f.name for f in Booking._meta.get_fields()}
                qs = Booking.objects.all()
                if "user" in fields:
                    qs = qs.filter(user=request.user)

                # prefetch to get titles/times if relations exist
                if Show:
                    qs = qs.select_related("show") if "show" in fields else qs
                data = []
                for b in qs.order_by("-id")[:100]:
                    # show id
                    show_id = getattr(b, "show_id", None)
                    if show_id is None and hasattr(b, "show") and getattr(b, "show", None):
                        show_id = getattr(b.show, "id", None)

                    # seat number
                    seat_no = None
                    if "seat_number" in fields:
                        seat_no = getattr(b, "seat_number", None)
                    elif "seat" in fields:
                        seat = getattr(b, "seat", None)
                        seat_no = getattr(seat, "number", None)

                    # movie title + show start time (best effort)
                    movie_title = None
                    show_start = None
                    show_obj = getattr(b, "show", None)
                    if not show_obj and Show and show_id:
                        try:
                            show_obj = Show.objects.get(id=show_id)
                        except Exception:
                            show_obj = None
                    if show_obj is not None:
                        show_start = getattr(show_obj, "start_time", None)
                        mov = getattr(show_obj, "movie", None)
                        if mov is None and Movie:
                            try:
                                mov = Movie.objects.get(id=getattr(show_obj, "movie_id", None))
                            except Exception:
                                mov = None
                        if mov is not None:
                            movie_title = getattr(mov, "title", getattr(mov, "name", None))

                    data.append({
                        "id": getattr(b, "id", 0),
                        "show_id": show_id,
                        "seat_number": str(seat_no) if seat_no is not None else None,
                        "movie_title": movie_title,
                        "show_start_time": show_start,
                    })

                if data:
                    return ok(data)
            except Exception:
                pass

        # Fallback to demo file (add same fields when possible)
        entries = _demo_read()
        data = []
        for e in entries:
            if e.get("user") != username:
                continue
            data.append({
                "id": e.get("id"),
                "show_id": e.get("show_id"),
                "seat_number": e.get("seat_number"),
                "movie_title": e.get("movie_title"),      # may be missing in older entries
                "show_start_time": e.get("show_start_time")
            })
        return ok(data)
