"""
Servicio de Aplicación para consultas públicas y paginadas de catálogos SISPRO.
Separa la lógica de paginación, filtrado y serialización de la capa HTTP.
"""

from typing import Any, Dict, List
from django.core.paginator import Paginator
from ..repositories import CatalogRepository
from ..serializers import (
    EpsLegacySerializer,
    EpsPanelSerializer,
    Cie10Serializer,
    CupsSerializer,
)


class CatalogQueryService:
    DEFAULT_PER_PAGE = 50

    @classmethod
    def search_public_entidades(cls, query_text: str = '', raw_limit: Any = 100) -> List[Dict[str, Any]]:
        limit = CatalogRepository.sanitize_limit(raw_limit)
        qs = CatalogRepository.build_eps_queryset(query_text=query_text)[:limit]
        return EpsLegacySerializer(qs, many=True).data

    @classmethod
    def search_public_cie10(cls, query_text: str = '', raw_limit: Any = 100) -> List[Dict[str, Any]]:
        limit = CatalogRepository.sanitize_limit(raw_limit)
        qs = CatalogRepository.build_cie10_queryset(query_text=query_text)[:limit]
        return Cie10Serializer(qs, many=True).data

    @classmethod
    def search_public_cups(cls, query_text: str = '', raw_limit: Any = 100) -> List[Dict[str, Any]]:
        limit = CatalogRepository.sanitize_limit(raw_limit)
        qs = CatalogRepository.build_cups_queryset(query_text=query_text)[:limit]
        return CupsSerializer(qs, many=True).data

    @classmethod
    def get_dashboard_stats(cls) -> Dict[str, int]:
        return CatalogRepository.get_counts()

    @classmethod
    def _paginate(cls, queryset, serializer_class, page_number: Any = 1, per_page: int = DEFAULT_PER_PAGE) -> Dict[str, Any]:
        paginator = Paginator(queryset, per_page)
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

    @classmethod
    def query_panel_entidades(cls, query_text: str = '', regimen: str = '', page: Any = 1) -> Dict[str, Any]:
        qs = CatalogRepository.build_eps_queryset(query_text=query_text, regimen=regimen, ordered=True)
        data = cls._paginate(qs, EpsPanelSerializer, page_number=page)
        data['regimenes'] = CatalogRepository.get_distinct_regimenes()
        return data

    @classmethod
    def query_panel_cie10(cls, query_text: str = '', page: Any = 1) -> Dict[str, Any]:
        qs = CatalogRepository.build_cie10_queryset(query_text=query_text, include_version=True, ordered=True)
        return cls._paginate(qs, Cie10Serializer, page_number=page)

    @classmethod
    def query_panel_cups(cls, query_text: str = '', page: Any = 1) -> Dict[str, Any]:
        qs = CatalogRepository.build_cups_queryset(query_text=query_text, include_version=True, ordered=True)
        return cls._paginate(qs, CupsSerializer, page_number=page)
