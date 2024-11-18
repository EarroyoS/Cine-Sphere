from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
import qrcode
from io import BytesIO

class TicketPDFGenerator:
    def __init__(self, ticket):
        self.ticket = ticket
        self.buffer = BytesIO()
        self.width, self.height = letter
        
    def generate_qr(self):
        """Generate QR code with ticket information"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = f"Ticket ID: {self.ticket.id}\nScreening: {self.ticket.screening.movie.title}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR image to bytes
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer)
        return qr_buffer.getvalue()

    def generate_pdf(self):
        # Create the PDF object using the buffer
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

        # Add cinema logo and header
        elements.append(Paragraph("CINEMA TICKETS", title_style))
        elements.append(Spacer(1, 12))

        # Ticket information
        info_style = styles["Normal"]
        info_style.fontSize = 12
        info_style.spaceAfter = 6

        # Format seat numbers
        seat_numbers = ", ".join([str(seat.number) for seat in self.ticket.seats.all()])
        
        # Create ticket information table
        data = [
            ["Movie:", self.ticket.screening.movie.title],
            ["Date & Time:", self.ticket.screening.start_time.strftime("%d/%m/%Y %H:%M")],
            ["Cinema:", self.ticket.screening.room.branch.name],
            ["Room:", f"Room {self.ticket.screening.room.number} ({self.ticket.screening.room.get_room_type_display()})"],
            ["Seats:", seat_numbers],
            ["Price:", f"${self.ticket.price}"],
            ["Ticket ID:", str(self.ticket.id)]
        ]

        # Create table
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 30))

        # Add terms and conditions
        terms_style = styles["Normal"]
        terms_style.fontSize = 8
        terms_style.textColor = colors.grey
        
        terms = """Terms and Conditions:
        1. This ticket is valid only for the specified date and time.
        2. Please arrive at least 15 minutes before the movie starts.
        3. Keep this ticket until the end of the movie.
        4. No refunds or exchanges allowed."""
        
        elements.append(Paragraph(terms, terms_style))

        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf