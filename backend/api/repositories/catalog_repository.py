"""
Repositorio de Acceso a Datos y Caché en Memoria para Catálogos Normativos SISPRO (EPS, CIE-10, CUPS).
Aísla el ORM de Django de la capa de servicios y controladores HTTP.
"""

import time
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, QuerySet
from ..models import Eps, Cie10, Cups


class CatalogRepository:
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 500
    CACHE_TTL_SECONDS = 60.0

    _stats_cache: Optional[Tuple[float, Dict[str, int]]] = None
    _regimenes_cache: Optional[Tuple[float, List[str]]] = None

    @classmethod
    def sanitize_limit(cls, raw_limit, default: int = DEFAULT_LIMIT) -> int:
        try:
            parsed = int(raw_limit)
        except (ValueError, TypeError):
            return default
        return max(1, min(parsed, cls.MAX_LIMIT))

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._stats_cache = None
        cls._regimenes_cache = None

    @classmethod
    def get_counts(cls) -> Dict[str, int]:
        now = time.monotonic()
        if cls._stats_cache is not None and (now - cls._stats_cache[0]) < cls.CACHE_TTL_SECONDS:
            return dict(cls._stats_cache[1])

        counts = {
            'count_entidades': Eps.objects.count(),
            'count_cie10': Cie10.objects.count(),
            'count_cups': Cups.objects.count(),
        }
        cls._stats_cache = (now, counts)
        return dict(counts)

    @classmethod
    def get_distinct_regimenes(cls) -> List[str]:
        now = time.monotonic()
        if cls._regimenes_cache is not None and (now - cls._regimenes_cache[0]) < cls.CACHE_TTL_SECONDS:
            return list(cls._regimenes_cache[1])

        qs = (
            Eps.objects.values_list('regimen', flat=True)
            .distinct()
            .order_by('regimen')
        )
        regimenes = [r for r in qs if r]
        cls._regimenes_cache = (now, regimenes)
        return list(regimenes)

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
