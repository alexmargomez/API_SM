import csv
from datetime import datetime
from django.http import HttpResponse
from api.models import Eps, Cie10, Cups


class CatalogExporterService:
    """
    Servicio encargado de exportar los catálogos maestros (Entidades, CIE10, CUPS)
    en formato CSV delimitado por punto y coma (;).
    """

    MODELS_MAP = {
        'entidades': (Eps, ['codigo', 'nombre', 'nit', 'regimen']),
        'cie10': (Cie10, ['codigo', 'descripcion', 'version', 'version_fecha']),
        'cups': (Cups, ['codigo', 'descripcion', 'version', 'version_fecha']),
    }

    @classmethod
    def export_to_csv_response(cls, entity: str) -> HttpResponse:
        if entity not in cls.MODELS_MAP:
            return HttpResponse('Entidad no encontrada', status=404)

        model, fields = cls.MODELS_MAP[entity]
        response = HttpResponse(content_type='text/csv; charset=utf-8')

        if entity in ['cie10', 'cups']:
            current_year = datetime.now().year
            filename = f'{entity}_{current_year}.csv'
            write_header = False
        else:
            filename = f'{entity}.csv'
            write_header = True

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response, delimiter=';')

        if write_header:
            writer.writerow(fields)

        for obj in model.objects.all().iterator():
            writer.writerow([getattr(obj, field) for field in fields])

        return response
