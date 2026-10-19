from datetime import datetime
import pandas as pd
from api.models import Eps, Cie10, Cups


class CatalogImporterService:
    """
    Servicio ETL encargado de procesar archivos .xlsx y .csv para actualizar
    los catálogos maestros de Entidades (EPS), AFP, CIE10 y CUPS.
    """

    ALLOWED_EXTENSIONS = ('.xlsx', '.csv')

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
    def _execute_etl(
        cls,
        uploaded_file,
        is_csv: bool,
        model,
        columns_map: dict,
        upload_type: str,
        hardcoded_fields: dict = None,
    ) -> dict:
        if is_csv:
            df = pd.read_csv(uploaded_file, sep=';', header=None, dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str)

        df.fillna('', inplace=True)

        extracted_data = {}
        for model_field, excel_col in columns_map.items():
            if isinstance(excel_col, int):
                if excel_col < len(df.columns):
                    extracted_data[model_field] = df.iloc[:, excel_col]
                else:
                    extracted_data[model_field] = ''
            else:
                if excel_col in df.columns:
                    extracted_data[model_field] = df[excel_col]
                else:
                    extracted_data[model_field] = ''

        df_clean = pd.DataFrame(extracted_data)

        if hardcoded_fields:
            for h_field, h_value in hardcoded_fields.items():
                df_clean[h_field] = h_value

        # Limpieza específica para EPS (remueve prefijos numéricos como "1. CONTRIBUTIVO")
        if model == Eps and 'regimen' in df_clean.columns:
            df_clean['regimen'] = (
                df_clean['regimen']
                .astype(str)
                .str.replace(r'^\d+\.\s*', '', regex=True)
            )

        # Limpieza previa del catálogo correspondiente
        if model == Eps:
            if upload_type == 'afp':
                model.objects.filter(regimen='AFP').delete()
            else:
                model.objects.exclude(regimen='AFP').delete()
        else:
            model.objects.all().delete()

        # Remover duplicados por la primera columna (código)
        first_field = list(columns_map.keys())[0]
        df_clean = df_clean.drop_duplicates(subset=[first_field])

        batch = []
        current_year = str(datetime.now().year)
        current_date = datetime.now().strftime('%Y-%m-%d')

        for row in df_clean.to_dict('records'):
            obj_data = {}
            for field in df_clean.columns:
                val = str(row.get(field, '')).strip() if field in row else ''
                if val.lower() == 'nan':
                    val = ''
                if field in ['codigo', 'version', 'version_fecha'] and val:
                    val = val[:50]
                obj_data[field] = val

            if model in [Cie10, Cups]:
                obj_data['version'] = current_year
                obj_data['version_fecha'] = current_date

            if not obj_data.get(first_field):
                continue

            batch.append(model(**obj_data))

        model.objects.bulk_create(batch, batch_size=1000)

        updated_count = len(batch)
        return {
            'updated_count': updated_count,
            'type': upload_type,
            'message': f'¡Se actualizaron {updated_count} registros de {upload_type.upper()} correctamente!',
        }
