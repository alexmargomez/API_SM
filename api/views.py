from django.http import JsonResponse
from django.db.models import Q
from .models import Eps, Cie10, Cups

def buscar_entidades(request):
    q = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 100))
    
    if q:
        query = Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(nit__icontains=q) | Q(regimen__icontains=q)
        resultados = Eps.objects.filter(query)[:limit]
    else:
        resultados = Eps.objects.all()[:limit]
        
    data = [
        {
            "ent_id": item.codigo,
            "ent_nombre": item.nombre,
            "nit": item.nit,
            "tps_rgm_nombre": item.regimen
        } for item in resultados
    ]
    return JsonResponse(data, safe=False)

def buscar_cie10(request):
    q = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 100))
    
    if q:
        query = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
        resultados = Cie10.objects.filter(query)[:limit]
    else:
        resultados = Cie10.objects.all()[:limit]
        
    data = [
        {
            "codigo": item.codigo,
            "descripcion": item.descripcion,
            "version": item.version,
            "version_fecha": item.version_fecha
        } for item in resultados
    ]
    return JsonResponse(data, safe=False)

def buscar_cups(request):
    q = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 100))
    
    if q:
        query = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
        resultados = Cups.objects.filter(query)[:limit]
    else:
        resultados = Cups.objects.all()[:limit]
        
    data = [
        {
            "codigo": item.codigo,
            "descripcion": item.descripcion,
            "version": item.version,
            "version_fecha": item.version_fecha
        } for item in resultados
    ]
    return JsonResponse(data, safe=False)
