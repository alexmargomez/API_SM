"""
Servicio de Aplicación para consultas públicas y paginadas de catálogos SISPRO.
Separa la lógica de negocio y serialización de la capa HTTP y delega el acceso a datos a CatalogRepository.
"""

from typing import Any, Dict, List
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
        page_data = CatalogRepository.paginate_queryset(queryset, page_number=page_number, per_page=per_page)
        serializer = serializer_class(page_data['items'], many=True)

        return {
            'results': serializer.data,
            'total': page_data['total'],
            'page': page_data['page'],
            'num_pages': page_data['num_pages'],
            'has_previous': page_data['has_previous'],
            'has_next': page_data['has_next'],
            'previous_page': page_data['previous_page'],
            'next_page': page_data['next_page'],
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
