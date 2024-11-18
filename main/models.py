from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_TYPES = [
        ('TRAD', 'Tradicional'),
        ('3D', '3D'),
        ('4DX', '4DX'),
    ]
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    number = models.IntegerField()
    room_type = models.CharField(max_length=4, choices=ROOM_TYPES, default='TRAD')
    capacity = models.IntegerField(default=60)  # Agregamos este campo

    def __str__(self):
        return f"{self.branch.name} - Sala {self.number} ({self.get_room_type_display()})"

    def create_seats(self):
        for seat_number in range(1, self.capacity + 1):
            Seat.objects.get_or_create(room=self, number=seat_number)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Guarda la sala primero
        self.create_seats()

class Movie(models.Model):
    CLASSIFICATIONS = [
        ('G', 'G'),
        ('PG', 'PG'),
        ('PG13', 'PG-13'),
        ('R', 'R'),
        ('NC17', 'NC-17'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField(help_text="Duración en minutos")
    image = models.ImageField(upload_to='movie_images/', null=True, blank=True)
    classification = models.CharField(max_length=4, choices=CLASSIFICATIONS)

    def __str__(self):
        return self.title

class Screening(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    cost = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  # Agregado valor por defecto

    def __str__(self):
        return f"{self.movie.title} - {self.room} - {self.start_time}"

    def available_seats(self):
        total_seats = 50  # Asumimos que todas las salas tienen 50 asientos
        occupied_seats = self.ticket_set.count()
        return total_seats - occupied_seats

class Seat(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    number = models.IntegerField()

    class Meta:
        unique_together = ['room', 'number']

    def __str__(self):
        return f"Sala {self.room.number} - Asiento {self.number}"

class DiscountCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)

    def __str__(self):
        return self.code

class TicketSeat(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='ticket_seats')
    seat = models.ForeignKey('Seat', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['ticket', 'seat']
        
    def __str__(self):
        return f"Ticket {self.ticket.id} - Seat {self.seat.number}"

class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat, through='TicketSeat')
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
    def add_seats(self, seat_numbers):
        seats_to_add = Seat.objects.filter(
            room=self.screening.room,
            number__in=seat_numbers
        )
        for seat in seats_to_add:
            TicketSeat.objects.create(ticket=self, seat=seat)