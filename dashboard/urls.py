from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard_index'),
    path('entidades/', views.manage_entidades, name='manage_entidades'),
    path('cie10/', views.manage_cie10, name='manage_cie10'),
    path('cups/', views.manage_cups, name='manage_cups'),
    path('importar/', views.import_data, name='import_data'),
    path('exportar/<str:entity>/', views.export_csv, name='export_csv'),
    path('docs/', views.api_docs, name='api_docs'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
