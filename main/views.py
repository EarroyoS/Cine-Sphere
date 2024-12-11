import logging
import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseServerError, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import login, logout, authenticate
from .forms import CustomUserCreationForm, UserUpdateForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Prefetch


from django.middleware.csrf import get_token

from .models import Movie, Branch, Screening, Seat, Ticket, DiscountCode, TicketSeat

logger = logging.getLogger(__name__)

def movie_list(request):
    movies = Movie.objects.all()
    return render(request, 'movie_list.html', {'movies': movies})

def movie_info(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    return render(request, 'movie_info.html', {'movie': movie})

def selector_cine(request, movie_id):
    try:
        movie = get_object_or_404(Movie, pk=movie_id)
        branches = Branch.objects.all()
        context = {'movie': movie, 'branches': branches}
        return render(request, 'selector_cine.html', context)
    except Exception as e:
        logger.error(f"Error in selector_cine view: {str(e)}")
        return HttpResponseServerError("Lo sentimos, ha ocurrido un error interno.")

def seat_selection(request, movie_id, branch_id, screening_id):
    movie = get_object_or_404(Movie, id=movie_id)
    branch = get_object_or_404(Branch, id=branch_id)
    screening = get_object_or_404(Screening, id=screening_id)

    # Obtener todos los asientos de la sala
    all_seats = Seat.objects.filter(room=screening.room).order_by('number')

    # Obtener los asientos ocupados para esta proyección
    occupied_seats = Ticket.objects.filter(screening=screening).values_list('seats__number', flat=True)

    # Crear una lista de diccionarios con la información de cada asiento
    seats_info = [
        {
            'number': seat.number,
            'is_occupied': seat.number in occupied_seats
        }
        for seat in all_seats
    ]

    context = {
        'movie': movie,
        'branch': branch,
        'screening': screening,
        'seats_info': seats_info,
    }
    return render(request, 'seat_selection.html', context)




def get_movie_screenings(request):
    movie_id = request.GET.get('movie_id')
    branch_id = request.GET.get('branch_id')
    
    print(f"Received request for movie_id: {movie_id}, branch_id: {branch_id}")
    
    if not movie_id or not branch_id:
        print("Missing movie_id or branch_id")
        return JsonResponse({'error': 'Missing movie_id or branch_id'}, status=400)
    
    screenings = Screening.objects.filter(
        movie_id=movie_id,
        room__branch_id=branch_id,
        start_time__gte=timezone.now()
    ).select_related('room').order_by('start_time')
    
    print(f"Found {screenings.count()} screenings")
    
    screening_data = [
        {
            'id': screening.id,
            'start_time': screening.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'room_number': screening.room.number,
            'room_type': screening.room.get_room_type_display(),
            'available_seats': screening.available_seats()
        }
        for screening in screenings
    ]
    
    print(f"Returning data for {len(screening_data)} screenings")
    
    return JsonResponse({'screenings': screening_data})

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io
import qrcode
import tempfile

@ensure_csrf_cookie
@require_POST
def create_ticket(request):
    try:
        # Agregar logging para debug
        logger.debug(f"Received request body: {request.body.decode()}")
        
        data = json.loads(request.body)
        logger.debug(f"Parsed JSON data: {data}")
        
        screening_id = data.get('screening')
        seat_numbers = data.get('seats')
        price = data.get('price')

        # Validación detallada de datos
        if not screening_id:
            return JsonResponse({'error': 'Falta el ID de la proyección'}, status=400)
        if not seat_numbers or not isinstance(seat_numbers, list):
            return JsonResponse({'error': 'Los asientos deben ser una lista de números'}, status=400)
        if price is None:
            return JsonResponse({'error': 'Falta el precio'}, status=400)

        try:
            price = float(price)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'El precio debe ser un número válido'}, status=400)

        screening = Screening.objects.get(id=screening_id)
        
        # Verificar si los asientos están disponibles
        occupied_seats = Ticket.objects.filter(
            screening=screening,
            seats__number__in=seat_numbers
        ).values_list('seats__number', flat=True)
        
        if occupied_seats:
            return JsonResponse({
                'error': f'Los siguientes asientos ya están ocupados: {list(occupied_seats)}'
            }, status=400)

        # Verificar que los asientos existen en la sala
        available_seats = Seat.objects.filter(
            room=screening.room,
            number__in=seat_numbers
        ).count()
        
        if available_seats != len(seat_numbers):
            return JsonResponse({
                'error': 'Uno o más asientos no existen en esta sala'
            }, status=400)

        # Crear el ticket
        ticket = Ticket.objects.create(
            screening=screening,
            price=price,
            user=request.user if request.user.is_authenticated else None
        )
        
        # Agregar los asientos al ticket
        ticket.add_seats(seat_numbers)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Generar el QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"{ticket.id}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Guardar la imagen del QR en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            qr_img.save(temp_file, format="PNG")
            temp_file_path = temp_file.name

        # Crear la tabla con los datos del ticket
        data = [
            ["Campo", "Información"],
            ["Película", screening.movie.title],
            ["Fecha y Hora", screening.start_time.strftime('%Y-%m-%d %H:%M:%S')],
            ["Sala", screening.room.number],
            ["Asiento(s)", ', '.join(map(str, seat_numbers))],
            ["Precio Total", f"${price:.2f}"]
        ]
        table = Table(data, colWidths=[2.5 * inch, 3.5 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(table)

        # Agregar el QR al PDF
        qr_image = Image(temp_file_path)
        qr_image.drawHeight = 1.5 * inch  # Ajusta el tamaño del QR
        qr_image.drawWidth = 1.5 * inch
        elements.append(qr_image)

        # Construir el PDF
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}.pdf"'
        return response

    except Exception as e:
        logger.error(f"Error creando ticket: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
@require_http_methods(["POST"])
def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        login(request, user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({
            'error': 'Usuario o contraseña incorrectos'
        }, status=400)


@require_http_methods(["POST"])
def register_view(request):
    form = CustomUserCreationForm(request.POST)  # Usa el formulario personalizado
    
    if form.is_valid():
        user = form.save()
        login(request, user)
        return JsonResponse({'success': True})
    else:
        errors = dict(form.errors.items())
        return JsonResponse({
            'error': 'Error en el formulario',
            'details': errors
        }, status=400)

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def update_user_info(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu información ha sido actualizada correctamente.')
            return redirect('/')  # Redirige a alguna página de perfil o donde desees
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'update_user_info.html', {'form': form})

@login_required
def ticket_history(request):
    # Obtener todos los tickets del usuario actual con sus relaciones
    tickets = Ticket.objects.filter(user=request.user)\
        .select_related('screening', 'screening__movie', 'screening__room')\
        .prefetch_related(
            Prefetch('ticket_seats', queryset=TicketSeat.objects.select_related('seat'))
        ).order_by('-screening__start_time')
    
    # Preparar los datos para la vista
    ticket_history = []
    for ticket in tickets:
        screening = ticket.screening
        movie = screening.movie
        
        # Obtener los números de asientos
        seat_numbers = [ts.seat.number for ts in ticket.ticket_seats.all()]
        seat_numbers.sort()
        
        can_cancel = screening.start_time > timezone.now()
        
        ticket_history.append({
            'ticket_id': ticket.id,
            'movie_title': movie.title,
            'screening_date': screening.start_time,
            'room_number': screening.room.number,
            'seats': ', '.join(map(str, seat_numbers)),
            'seat_count': len(seat_numbers),
            'price': ticket.price,
            'can_cancel': can_cancel,
            'discount_applied': True if ticket.discount_code else False
        })
    
    return render(request, 'ticket_history.html', {
        'tickets': ticket_history
    })

@login_required
def cancel_ticket(request, ticket_id):
    try:
        ticket = Ticket.objects.select_related('screening').get(
            id=ticket_id,
            user=request.user
        )
        
        # Verificar si el screening aún no ha ocurrido
        if ticket.screening.start_time > timezone.now():
            # Eliminar las relaciones de asientos
            TicketSeat.objects.filter(ticket=ticket).delete()
            # Si hay un código de descuento, decrementar su uso
            if ticket.discount_code:
                ticket.discount_code.current_uses -= 1
                ticket.discount_code.save()
            # Eliminar el ticket
            ticket.delete()
            return redirect('ticket_history')
        else:
            return redirect('ticket_history')
            
    except Ticket.DoesNotExist:
        return redirect('ticket_history')