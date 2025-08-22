from rest_framework import serializers
from .models import Movie, Screen, Show, Seat, Booking

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "title", "description", "duration_min", "rating"]

class ScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screen
        fields = ["id", "name", "rows", "cols"]

class ShowSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    screen = serializers.StringRelatedField()
    class Meta:
        model = Show
        fields = ["id", "movie", "screen", "start_time", "price"]

class SeatSerializer(serializers.ModelSerializer):
    screen = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Seat
        fields = ["id", "row", "col", "screen"]

class BookingCreateSerializer(serializers.Serializer):
    show_id = serializers.IntegerField()
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )
    def validate_seat_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate seat IDs are not allowed.")
        return value

class BookingSerializer(serializers.ModelSerializer):
    show = ShowSerializer(read_only=True)
    seats = SeatSerializer(many=True, read_only=True)
    class Meta:
        model = Booking
        fields = ["id", "show", "seats", "total_amount", "status", "created_at"]
 
