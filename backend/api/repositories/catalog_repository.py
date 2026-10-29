"""
Repositorio de Acceso a Datos y Caché Unificada para Catálogos Normativos SISPRO (EPS, CIE-10, CUPS).
Aísla el ORM de Django y la paginación de la capa de servicios y controladores HTTP.
"""

from typing import Any, Dict, List
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from ..models import Eps, Cie10, Cups


class CatalogRepository:
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 500
    CACHE_TTL_SECONDS = 60

    STATS_CACHE_KEY = 'api_sm:catalog:counts'
    REGIMENES_CACHE_KEY = 'api_sm:catalog:regimenes'

    @classmethod
    def sanitize_limit(cls, raw_limit, default: int = DEFAULT_LIMIT) -> int:
        try:
            parsed = int(raw_limit)
        except (ValueError, TypeError):
            return default
        return max(1, min(parsed, cls.MAX_LIMIT))

    @classmethod
    def invalidate_cache(cls) -> None:
        cache.delete_many([cls.STATS_CACHE_KEY, cls.REGIMENES_CACHE_KEY])

    @classmethod
    def get_counts(cls) -> Dict[str, int]:
        cached = cache.get(cls.STATS_CACHE_KEY)
        if cached is not None:
            return dict(cached)

        counts = {
            'count_entidades': Eps.objects.count(),
            'count_cie10': Cie10.objects.count(),
            'count_cups': Cups.objects.count(),
        }
        cache.set(cls.STATS_CACHE_KEY, counts, timeout=cls.CACHE_TTL_SECONDS)
        return dict(counts)

    @classmethod
    def get_distinct_regimenes(cls) -> List[str]:
        cached = cache.get(cls.REGIMENES_CACHE_KEY)
        if cached is not None:
            return list(cached)

        qs = (
            Eps.objects.values_list('regimen', flat=True)
            .distinct()
            .order_by('regimen')
        )
        regimenes = [r for r in qs if r]
        cache.set(cls.REGIMENES_CACHE_KEY, regimenes, timeout=cls.CACHE_TTL_SECONDS)
        return list(regimenes)

    @classmethod
    def paginate_queryset(cls, queryset: QuerySet, page_number: Any = 1, per_page: int = 50) -> Dict[str, Any]:
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page_number)
        return {
            'items': list(page_obj.object_list),
            'total': paginator.count,
            'page': page_obj.number,
            'num_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        }

    @classmethod
    def build_eps_queryset(cls, query_text: str = '', regimen: str = '', ordered: bool = False) -> QuerySet:
        qs = Eps.objects.all()
        if ordered:
            qs = qs.order_by('id')
        q = (query_text or '').strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(codigo__icontains=q)
                | Q(nit__icontains=q)
                | Q(regimen__icontains=q)
            )
        reg = (regimen or '').strip()
        if reg:
            qs = qs.filter(regimen__iexact=reg)
        return qs

    @classmethod
    def build_cie10_queryset(cls, query_text: str = '', include_version: bool = False, ordered: bool = False) -> QuerySet:
        qs = Cie10.objects.all()
        if ordered:
            qs = qs.order_by('id')
        q = (query_text or '').strip()
        if q:
            condition = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
            if include_version:
                condition = condition | Q(version__icontains=q) | Q(version_fecha__icontains=q)
            qs = qs.filter(condition)
        return qs

    @classmethod
    def build_cups_queryset(cls, query_text: str = '', include_version: bool = False, ordered: bool = False) -> QuerySet:
        qs = Cups.objects.all()
        if ordered:
            qs = qs.order_by('id')
        q = (query_text or '').strip()
        if q:
            condition = Q(descripcion__icontains=q) | Q(codigo__icontains=q)
            if include_version:
                condition = condition | Q(version__icontains=q) | Q(version_fecha__icontains=q)
            qs = qs.filter(condition)
        return qs

    @classmethod
    def resolve_catalog_codes_map(
        cls,
        cie10_codes: set,
        cups_codes: set,
        eps_codes: set,
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Resuelve en lote los códigos CIE-10, CUPS y EPS presentes en un Bundle FHIR sin exponer el ORM a los servicios."""
        cie10_map: Dict[str, Dict[str, str]] = {}
        cups_map: Dict[str, Dict[str, str]] = {}
        eps_map: Dict[str, Dict[str, str]] = {}

        if cie10_codes:
            for obj in Cie10.objects.filter(codigo__in=list(cie10_codes)):
                cie10_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'descripcion': obj.descripcion,
                    'version': obj.version or '',
                }

        if cups_codes:
            for obj in Cups.objects.filter(codigo__in=list(cups_codes)):
                cups_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'descripcion': obj.descripcion,
                    'version': obj.version or '',
                }

        if eps_codes:
            for obj in Eps.objects.filter(codigo__in=list(eps_codes)):
                eps_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'nombre': obj.nombre,
                    'nit': obj.nit or '',
                    'regimen': obj.regimen or '',
                }

        return {'cie10': cie10_map, 'cups': cups_map, 'eps': eps_map}

