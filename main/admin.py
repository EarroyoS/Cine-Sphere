from django.contrib import admin
from .models import Branch, Room, Movie, Screening, Seat, DiscountCode, Ticket

# Register your models here.
admin.site.register(Branch)
admin.site.register(Room)
admin.site.register(Movie)
admin.site.register(Screening)
admin.site.register(Seat)
admin.site.register(DiscountCode)
admin.site.register(Ticket)