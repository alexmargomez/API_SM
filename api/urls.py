from django.urls import path
from . import views

urlpatterns = [
    path('entidades', views.buscar_entidades, name='api_entidades'),
    path('cie10', views.buscar_cie10, name='api_cie10'),
    path('cups', views.buscar_cups, name='api_cups'),
]
