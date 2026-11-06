import csv
from datetime import datetime
from django.http import HttpResponse, StreamingHttpResponse
from api.models import Eps, Cie10, Cups


class _EchoCsvBuffer:
    """Buffer ligero O(1) para escritura en streaming de csv.writer."""

    def write(self, value: str) -> str:
        return value


class CatalogExporterService:
    """
    Servicio encargado de exportar los catálogos maestros (Entidades, CIE10, CUPS)
    en formato CSV delimitado por punto y coma (;) mediante StreamingHttpResponse O(1).
    """

    MODELS_MAP = {
        'entidades': (Eps, ['codigo', 'nombre', 'nit', 'regimen']),
        'cie10': (Cie10, ['codigo', 'descripcion', 'version', 'version_fecha']),
        'cups': (Cups, ['codigo', 'descripcion', 'version', 'version_fecha']),
    }

    @classmethod
    def export_to_csv_response(cls, entity: str):
        if entity not in cls.MODELS_MAP:
            return HttpResponse('Entidad no encontrada', status=404)

        model, fields = cls.MODELS_MAP[entity]

        if entity in ['cie10', 'cups']:
            current_year = datetime.now().year
            filename = f'{entity}_{current_year}.csv'
            write_header = False
        else:
            filename = f'{entity}.csv'
            write_header = True

        pseudo_buffer = _EchoCsvBuffer()
        writer = csv.writer(pseudo_buffer, delimiter=';')

        def row_generator():
            if write_header:
                yield '\ufeff'
                yield writer.writerow(fields)
            for obj in model.objects.all().order_by('id').iterator(chunk_size=1000):
                yield writer.writerow([getattr(obj, field) for field in fields])

        response = StreamingHttpResponse(
            row_generator(),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
