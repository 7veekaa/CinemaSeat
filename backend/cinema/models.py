from django.db import models
from django.conf import settings

class Movie(models.Model):
    title=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    duration_min=models.PositiveIntegerField()
    rating=models.CharField(max_length=10, blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class Screen(models.Model):
    name=models.CharField(max_length=100, unique=True)
    rows=models.PositiveIntegerField()
    cols=models.PositiveIntegerField()
    def __str__(self): return self.name

class Show(models.Model):
    movie=models.ForeignKey('cinema.Movie', on_delete=models.CASCADE, related_name="shows")
    screen=models.ForeignKey('cinema.Screen', on_delete=models.PROTECT, related_name="shows")
    start_time=models.DateTimeField(db_index=True)
    price=models.DecimalField(max_digits=8, decimal_places=2, default=250)
    class Meta:
        unique_together=("screen","start_time")
        ordering=["start_time"]
    def __str__(self): return f"{self.movie.title} @ {self.start_time:%Y-%m-%d %H:%M}"

class Seat(models.Model):
    screen=models.ForeignKey('cinema.Screen', on_delete=models.CASCADE, related_name="seats")
    row=models.PositiveIntegerField()
    col=models.PositiveIntegerField()
    class Meta:
        unique_together=("screen","row","col")
        ordering=["row","col"]
    def __str__(self): return f"{self.screen.name}-{self.row}-{self.col}"

class Booking(models.Model):
    PENDING="PENDING"
    CONFIRMED="CONFIRMED"
    CANCELLED="CANCELLED"
    STATUS_CHOICES=[(PENDING,"PENDING"),(CONFIRMED,"CONFIRMED"),(CANCELLED,"CANCELLED")]

    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cinema_bookings")
    show=models.ForeignKey('cinema.Show', on_delete=models.CASCADE, related_name="bookings")
    seats=models.ManyToManyField('cinema.Seat', related_name="bookings")
    total_amount=models.DecimalField(max_digits=10, decimal_places=2)
    status=models.CharField(max_length=10, choices=STATUS_CHOICES, default=CONFIRMED)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["-created_at"]
    def __str__(self): return f"Booking {self.id} by {self.user}"
