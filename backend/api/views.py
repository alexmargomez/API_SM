from django.contrib.auth import authenticate
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Eps, Cie10, Cups
from .serializers import (
    EpsLegacySerializer,
    EpsPanelSerializer,
    Cie10Serializer,
    CupsSerializer,
)
from .services import CatalogImporterService, CatalogExporterService


# ============================================================================
# 1. ENDPOINTS PÚBLICOS DE INTEGRACIÓN EXTERNA (Retrocompatibilidad Software Médico)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_entidades(request):
    q = request.GET.get('q', '').strip()
    try:
        limit = int(request.GET.get('limit', 100))
    except ValueError:
        limit = 100

    queryset = Eps.objects.all()
    if q:
        query = (
            Q(nombre__icontains=q)
            | Q(codigo__icontains=q)
            | Q(nit__icontains=q)
            | Q(regimen__icontains=q)
        )
        queryset = queryset.filter(query)

    resultados = queryset[:limit]
    serializer = EpsLegacySerializer(resultados, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_cie10(request):
    q = request.GET.get('q', '').strip()
    try:
        limit = int(request.GET.get('limit', 100))
    except ValueError:
        limit = 100

    queryset = Cie10.objects.all()
    if q:
        query = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
        queryset = queryset.filter(query)

    resultados = queryset[:limit]
    serializer = Cie10Serializer(resultados, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_cups(request):
    q = request.GET.get('q', '').strip()
    try:
        limit = int(request.GET.get('limit', 100))
    except ValueError:
        limit = 100

    queryset = Cups.objects.all()
    if q:
        query = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
        queryset = queryset.filter(query)

    resultados = queryset[:limit]
    serializer = CupsSerializer(resultados, many=True)
    return Response(serializer.data)


# ============================================================================
# 2. ENDPOINTS DEL PANEL ADMINISTRATIVO SPA (Vue 3)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def panel_stats(request):
    return Response({
        'count_entidades': Eps.objects.count(),
        'count_cie10': Cie10.objects.count(),
        'count_cups': Cups.objects.count(),
    })


def _paginate_queryset(request, queryset, serializer_class, per_page=50):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    serializer = serializer_class(page_obj.object_list, many=True)

    return {
        'results': serializer.data,
        'total': paginator.count,
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_entidades(request):
    q = request.GET.get('q', '').strip()
    regimen_filter = request.GET.get('regimen', '').strip()

    queryset = Eps.objects.all().order_by('id')

    if q:
        query = (
            Q(codigo__icontains=q)
            | Q(nombre__icontains=q)
            | Q(nit__icontains=q)
            | Q(regimen__icontains=q)
        )
        queryset = queryset.filter(query)

    if regimen_filter:
        queryset = queryset.filter(regimen__iexact=regimen_filter)

    data = _paginate_queryset(request, queryset, EpsPanelSerializer)

    regimenes = (
        Eps.objects.values_list('regimen', flat=True)
        .distinct()
        .order_by('regimen')
    )
    data['regimenes'] = [r for r in regimenes if r]
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_cie10(request):
    q = request.GET.get('q', '').strip()
    queryset = Cie10.objects.all().order_by('id')

    if q:
        query = (
            Q(codigo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(version__icontains=q)
            | Q(version_fecha__icontains=q)
        )
        queryset = queryset.filter(query)

    data = _paginate_queryset(request, queryset, Cie10Serializer)
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_cups(request):
    q = request.GET.get('q', '').strip()
    queryset = Cups.objects.all().order_by('id')

    if q:
        query = (
            Q(codigo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(version__icontains=q)
            | Q(version_fecha__icontains=q)
        )
        queryset = queryset.filter(query)

    data = _paginate_queryset(request, queryset, CupsSerializer)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def panel_import(request):
    if not request.user.is_superuser:
        return Response(
            {'error': 'No tienes permisos de superusuario para importar catálogos.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    upload_type = request.data.get('type', '').strip()
    uploaded_file = request.FILES.get('file')

    try:
        result = CatalogImporterService.process_upload(
            upload_type=upload_type,
            uploaded_file=uploaded_file,
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response(
            {'error': f'Error procesando el archivo: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_export_csv(request, entity):
    return CatalogExporterService.export_to_csv_response(entity)


# ============================================================================
# 3. ENDPOINTS DE AUTENTICACIÓN (Token Bearer para Panel Vue 3)
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def auth_login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response(
            {'error': 'Por favor ingresa usuario y contraseña.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Usuario o contraseña incorrectos.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_superuser:
        return Response(
            {'error': 'Acceso restringido únicamente a administradores.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': {
            'username': user.username,
            'is_superuser': user.is_superuser,
        },
        'message': f'¡Bienvenido de nuevo, {user.username}!',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    if hasattr(request.user, 'auth_token'):
        request.user.auth_token.delete()
    return Response({'message': 'Has cerrado sesión exitosamente.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    return Response({
        'user': {
            'username': request.user.username,
            'is_superuser': request.user.is_superuser,
        }
    })
