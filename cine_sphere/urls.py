"""
URL configuration for cine_sphere project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from main import views



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.movie_list,  name='movie_list'),
    path('<int:movie_id>/', views.movie_info, name='movie_info'),
    path('<int:movie_id>/selector/', views.selector_cine, name='selector_cine'),
    path('<int:movie_id>/<int:branch_id>/<int:screening_id>/', views.seat_selection, name='seat_selection'),
    path('get_movie_screenings/', views.get_movie_screenings, name='get_movie_screenings'),
    path('api/tickets/create/', views.create_ticket, name='create_ticket'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('update-info/', views.update_user_info, name='update_user_info'),
    path('tickets/history/', views.ticket_history, name='ticket_history'),
    path('tickets/cancel/<int:ticket_id>/', views.cancel_ticket, name='cancel_ticket'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
