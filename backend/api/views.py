"""
Controladores HTTP Delgados (Thin Controllers) para API_SM.
Delegan toda la lógica de negocio, acceso a datos y caché a la capa de Servicios y Repositorios.
"""

import json as _json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .repositories import CatalogRepository
from .services import (
    CatalogImporterService,
    CatalogExporterService,
    FhirBundleInspectorService,
    CatalogQueryService,
    AdminAuthService,
    AuthValidationError,
    AuthCredentialsError,
    AuthForbiddenError,
)


# ============================================================================
# 1. ENDPOINTS PÚBLICOS DE INTEGRACIÓN EXTERNA (Retrocompatibilidad Software Médico)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_entidades(request):
    data = CatalogQueryService.search_public_entidades(
        query_text=request.GET.get('q', ''),
        raw_limit=request.GET.get('limit', 100),
    )
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_cie10(request):
    data = CatalogQueryService.search_public_cie10(
        query_text=request.GET.get('q', ''),
        raw_limit=request.GET.get('limit', 100),
    )
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_cups(request):
    data = CatalogQueryService.search_public_cups(
        query_text=request.GET.get('q', ''),
        raw_limit=request.GET.get('limit', 100),
    )
    return Response(data)


# ============================================================================
# 2. ENDPOINTS DEL PANEL ADMINISTRATIVO SPA (Vue 3)
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def panel_stats(request):
    return Response(CatalogQueryService.get_dashboard_stats())


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_entidades(request):
    data = CatalogQueryService.query_panel_entidades(
        query_text=request.GET.get('q', ''),
        regimen=request.GET.get('regimen', ''),
        page=request.GET.get('page', 1),
    )
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_cie10(request):
    data = CatalogQueryService.query_panel_cie10(
        query_text=request.GET.get('q', ''),
        page=request.GET.get('page', 1),
    )
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def panel_cups(request):
    data = CatalogQueryService.query_panel_cups(
        query_text=request.GET.get('q', ''),
        page=request.GET.get('page', 1),
    )
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
        CatalogRepository.invalidate_cache()
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
    try:
        payload = AdminAuthService.login_superuser(
            request=request,
            username=request.data.get('username', ''),
            password=request.data.get('password', ''),
        )
        return Response(payload, status=status.HTTP_200_OK)
    except AuthValidationError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except AuthCredentialsError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
    except AuthForbiddenError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    return Response(AdminAuthService.logout_user(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    return Response(AdminAuthService.get_user_profile(request.user))


# ============================================================================
# 4. HERRAMIENTAS TÉCNICAS (Inspector y Traductor FHIR Resolución 1888 / IHCE)
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def inspect_fhir_bundle(request):
    if request.method == 'GET':
        sample = FhirBundleInspectorService.get_sample_bundle()
        result = FhirBundleInspectorService.inspect_payload(sample)
        result['sample_raw_json'] = _json.dumps(sample, indent=2, ensure_ascii=False)
        return Response(result, status=status.HTTP_200_OK)

    uploaded_file = request.FILES.get('file')
    if uploaded_file is not None:
        try:
            raw_input = uploaded_file.read().decode('utf-8-sig', errors='replace')
        except Exception as exc:
            return Response(
                {'error': f'No se pudo leer el archivo subido: {str(exc)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        payload = request.data
        raw_input = payload
        if isinstance(payload, dict):
            if 'raw_json' in payload:
                raw_input = payload.get('raw_json')
            elif 'bundle' in payload and 'resourceType' not in payload:
                raw_input = payload.get('bundle')

    try:
        result = FhirBundleInspectorService.inspect_payload(raw_input)
        return Response(result, status=status.HTTP_200_OK)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response(
            {'error': f'Error al analizar el Bundle FHIR: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
