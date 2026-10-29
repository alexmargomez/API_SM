import csv
import io
import re
from datetime import datetime
from django.db import transaction
from api.models import Eps, Cie10, Cups


class CatalogImporterService:
    """
    Servicio ETL transaccional encargado de procesar archivos .xlsx y .csv para actualizar
    los catálogos maestros de Entidades (EPS), AFP, CIE10 y CUPS.
    Incluye:
      - Streaming nativo CSV sin sobrecarga de Pandas en memoria.
      - Lazy-loading de Pandas/OpenPyXL exclusivamente cuando se suben archivos .xlsx.
      - Transaccionalidad atómica (transaction.atomic) para evitar pérdida de catálogos ante fallos parciales.
    """

    ALLOWED_EXTENSIONS = ('.xlsx', '.csv')
    HEADER_TOKENS = {'codigo', 'código', 'code', 'nombre', 'descripcion', 'descripción'}

    @classmethod
    def process_upload(cls, upload_type: str, uploaded_file) -> dict:
        if not uploaded_file:
            raise ValueError('No se proporcionó ningún archivo para importar.')

        filename = uploaded_file.name or ''
        if not filename.lower().endswith(cls.ALLOWED_EXTENSIONS):
            raise ValueError('El archivo debe estar en formato .xlsx o .csv')

        is_csv = filename.lower().endswith('.csv')

        if upload_type == 'entidades':
            model = Eps
            columns_map = {
                'codigo': 'Codigo',
                'nombre': 'Nombre',
                'nit': 'Extra_V:Poblacion',
                'regimen': 'Extra_IX',
            }
            hardcoded_fields = None
        elif upload_type == 'afp':
            model = Eps
            columns_map = {
                'codigo': 'Codigo',
                'nombre': 'Nombre',
                'nit': 'Extra_I',
            }
            hardcoded_fields = {'regimen': 'AFP'}
        elif upload_type == 'cie10':
            model = Cie10
            columns_map = (
                {'codigo': 0, 'descripcion': 1}
                if is_csv
                else {'codigo': 'Codigo', 'descripcion': 'Nombre'}
            )
            hardcoded_fields = None
        elif upload_type == 'cups':
            model = Cups
            columns_map = (
                {'codigo': 0, 'descripcion': 1}
                if is_csv
                else {'codigo': 'Codigo', 'descripcion': 'Nombre'}
            )
            hardcoded_fields = None
        else:
            raise ValueError(f"Tipo de importación no válido: '{upload_type}'.")

        return cls._execute_etl(
            uploaded_file=uploaded_file,
            is_csv=is_csv,
            model=model,
            columns_map=columns_map,
            upload_type=upload_type,
            hardcoded_fields=hardcoded_fields,
        )

    @classmethod
    def _extract_records(cls, uploaded_file, is_csv: bool, columns_map: dict) -> list:
        records = []
        if is_csv:
            raw_bytes = uploaded_file.read()
            text_content = raw_bytes.decode('utf-8-sig', errors='replace')
            reader = csv.reader(io.StringIO(text_content), delimiter=';')
            for row_idx, row in enumerate(reader):
                if not row:
                    continue
                if row_idx == 0 and row[0].strip().lower() in cls.HEADER_TOKENS:
                    continue
                item = {}
                for model_field, col_spec in columns_map.items():
                    if isinstance(col_spec, int):
                        item[model_field] = row[col_spec].strip() if col_spec < len(row) else ''
                    else:
                        item[model_field] = ''
                records.append(item)
            return records

        # Lazy import de pandas solo para archivos Excel (.xlsx)
        import pandas as pd

        df = pd.read_excel(uploaded_file, dtype=str)
        df.fillna('', inplace=True)

        for _, row in df.iterrows():
            item = {}
            for model_field, excel_col in columns_map.items():
                if isinstance(excel_col, int):
                    item[model_field] = str(row.iloc[excel_col]).strip() if excel_col < len(df.columns) else ''
                else:
                    item[model_field] = str(row[excel_col]).strip() if excel_col in df.columns else ''
            records.append(item)
        return records

    @classmethod
    def _execute_etl(
        cls,
        uploaded_file,
        is_csv: bool,
        model,
        columns_map: dict,
        upload_type: str,
        hardcoded_fields: dict = None,
    ) -> dict:
        raw_records = cls._extract_records(uploaded_file, is_csv, columns_map)
        first_field = list(columns_map.keys())[0]
        seen_keys = set()
        batch = []
        current_year = str(datetime.now().year)
        current_date = datetime.now().strftime('%Y-%m-%d')

        for row in raw_records:
            obj_data = dict(row)
            if hardcoded_fields:
                obj_data.update(hardcoded_fields)

            if model == Eps and 'regimen' in obj_data:
                obj_data['regimen'] = re.sub(r'^\d+\.\s*', '', str(obj_data.get('regimen', '')).strip())

            for field, val in list(obj_data.items()):
                clean_val = str(val or '').strip()
                if clean_val.lower() == 'nan':
                    clean_val = ''
                if field in ['codigo', 'version', 'version_fecha'] and clean_val:
                    clean_val = clean_val[:50]
                obj_data[field] = clean_val

            primary_code = obj_data.get(first_field, '')
            if not primary_code or primary_code in seen_keys:
                continue
            seen_keys.add(primary_code)

            if model in [Cie10, Cups]:
                obj_data['version'] = current_year
                obj_data['version_fecha'] = current_date

            batch.append(model(**obj_data))

        with transaction.atomic():
            if model == Eps:
                if upload_type == 'afp':
                    model.objects.filter(regimen='AFP').delete()
                else:
                    model.objects.exclude(regimen='AFP').delete()
            else:
                model.objects.all().delete()

            model.objects.bulk_create(batch, batch_size=1000)

        updated_count = len(batch)
        return {
            'updated_count': updated_count,
            'type': upload_type,
            'message': f'¡Se actualizaron {updated_count} registros de {upload_type.upper()} correctamente!',
        }
