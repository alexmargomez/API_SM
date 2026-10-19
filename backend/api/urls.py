from django.urls import path
from . import views

urlpatterns = [
    # Endpoints públicos de integración externa (retrocompatibles)
    path('entidades', views.buscar_entidades, name='api_entidades'),
    path('cie10', views.buscar_cie10, name='api_cie10'),
    path('cups', views.buscar_cups, name='api_cups'),

    # Endpoints del panel administrativo SPA (Vue 3)
    path('panel/stats/', views.panel_stats, name='panel_stats'),
    path('panel/entidades/', views.panel_entidades, name='panel_entidades'),
    path('panel/cie10/', views.panel_cie10, name='panel_cie10'),
    path('panel/cups/', views.panel_cups, name='panel_cups'),
    path('panel/import/', views.panel_import, name='panel_import'),
    path('panel/export/<str:entity>/', views.panel_export_csv, name='panel_export_csv'),

    # Endpoints de autenticación del panel
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),
    path('auth/me/', views.auth_me, name='auth_me'),
]
