import pandas as pd
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from api.models import Eps, Cie10, Cups

def index(request):
    context = {
        'count_entidades': Eps.objects.count(),
        'count_cie10': Cie10.objects.count(),
        'count_cups': Cups.objects.count(),
    }
    return render(request, 'dashboard/index.html', context)

def api_docs(request):
    return render(request, 'dashboard/docs.html')

def _handle_upload(request, model, columns_map, template_name=None, context_name=None, upload_type=None, hardcoded_fields=None):
    if request.method == 'POST' and request.FILES.get('file'):
        excel_file = request.FILES['file']
        if not excel_file.name.endswith(('.xlsx', '.csv')):
            messages.error(request, 'El archivo debe ser formato .xlsx o .csv')
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file, sep=';', header=None, dtype=str)
            else:
                df = pd.read_excel(excel_file, dtype=str)
                
            df.fillna('', inplace=True)
            
            # Extraer solo las columnas mapeadas, si existen en el DataFrame
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
            
            # Limpieza específica para EPS (luego de mapear las columnas)
            if model == Eps and 'regimen' in df_clean.columns:
                df_clean['regimen'] = df_clean['regimen'].astype(str).str.replace(r'^\d+\.\s*', '', regex=True)
            
            # Borramos la base actual e insertamos
            if model == Eps:
                if upload_type == 'afp':
                    model.objects.filter(regimen='AFP').delete()
                else:
                    model.objects.exclude(regimen='AFP').delete()
            else:
                model.objects.all().delete()
            
            # Remover duplicados por la primera columna (código) para evitar IntegrityError
            first_field = list(columns_map.keys())[0]
            df_clean = df_clean.drop_duplicates(subset=[first_field])
            
            batch = []
            from datetime import datetime
            current_year = str(datetime.now().year)
            
            for row in df_clean.to_dict('records'):
                obj_data = {}
                for field in df_clean.columns:
                    val = str(row.get(field, '')) if field in row else ''
                    if val == 'nan': val = ''
                    # Truncar los campos a la longitud máxima de la base de datos (50 para codigo/version)
                    if field in ['codigo', 'version', 'version_fecha'] and val:
                        val = val[:50]
                    obj_data[field] = val
                
                # Reglas de negocio forzadas:
                if model in [Cie10, Cups]:
                    obj_data['version'] = current_year
                    obj_data['version_fecha'] = datetime.now().strftime('%Y-%m-%d')
                    
                # Ignorar filas vacías o sin código principal
                first_field = list(columns_map.keys())[0]  # usualmente 'codigo'
                if not obj_data.get(first_field):
                    continue
                    
                batch.append(model(**obj_data))
                
            model.objects.bulk_create(batch, batch_size=1000)            
            messages.success(request, f'¡Se actualizaron {len(df_clean)} registros correctamente!')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        except Exception as e:
            messages.error(request, f'Error procesando el archivo: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
    # Si template_name es None, significa que llamamos esto solo para procesar (como en import_data)
    if not template_name:
        return redirect(request.META.get('HTTP_REFERER', '/'))
        
    q = request.GET.get('q', '').strip()
    regimen_filter = request.GET.get('regimen', '').strip()
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    resultados = model.objects.all()
    
    if q:
        # Buscamos en todas las columnas de forma genérica
        fields = list(columns_map.keys())
        query = Q()
        for field in fields:
            query |= Q(**{f'{field}__icontains': q})
        resultados = resultados.filter(query)
        
    # Aplicar filtro de régimen si el modelo es Eps y hay un régimen seleccionado
    if model.__name__ == 'Eps' and regimen_filter:
        resultados = resultados.filter(regimen__iexact=regimen_filter)
        
    paginator = Paginator(resultados, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
        
    context = {
        context_name: page_obj,  # Mantenemos por si la vista lo usa
        'page_obj': page_obj,
        'total': paginator.count,
        'q': q
    }
    
    if model.__name__ == 'Eps':
        regimenes = model.objects.values_list('regimen', flat=True).distinct().order_by('regimen')
        context['regimenes'] = [r for r in regimenes if r]
        context['selected_regimen'] = regimen_filter
    
    # Si es una petición AJAX, solo renderizar el parcial de la tabla
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        partial_template = template_name.replace('dashboard/', 'dashboard/partials/').replace('.html', '_table.html')
        return render(request, partial_template, context)
        
    return render(request, template_name, context)

def manage_entidades(request):
    columns_map = {
        'codigo': 'Codigo',
        'nombre': 'Nombre',
        'nit': 'Extra_V:Poblacion',
        'regimen': 'Extra_IX'
    }
    return _handle_upload(
        request, Eps, 
        columns_map, 
        'dashboard/entidades.html', 
        'entidades',
        upload_type='entidades'
    )

def manage_cie10(request):
    columns_map = {
        'codigo': 0,
        'descripcion': 1,
        'version': 2,
        'version_fecha': 3
    }
    return _handle_upload(
        request, Cie10, 
        columns_map, 
        'dashboard/cie10.html', 
        'registros'
    )

def manage_cups(request):
    columns_map = {
        'codigo': 0,
        'descripcion': 1,
        'version': 2,
        'version_fecha': 3
    }
    return _handle_upload(
        request, Cups, 
        columns_map, 
        'dashboard/cups.html', 
        'registros'
    )

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser, login_url='login')
def import_data(request):
    if request.method == 'POST':
        upload_type = request.POST.get('type')
        excel_file = request.FILES.get('file')
        if not excel_file:
            return render(request, 'dashboard/import.html')
            
        is_csv = excel_file.name.endswith('.csv')
        
        if upload_type == 'entidades':
            columns_map = {'codigo': 'Codigo', 'nombre': 'Nombre', 'nit': 'Extra_V:Poblacion', 'regimen': 'Extra_IX'}
            return _handle_upload(request, Eps, columns_map, upload_type='entidades')
        elif upload_type == 'afp':
            columns_map = {'codigo': 'Codigo', 'nombre': 'Nombre', 'nit': 'Extra_I'}
            return _handle_upload(request, Eps, columns_map, upload_type='afp', hardcoded_fields={'regimen': 'AFP'})
        elif upload_type == 'cie10':
            if is_csv:
                columns_map = {'codigo': 0, 'descripcion': 1}
            else:
                columns_map = {'codigo': 'Codigo', 'descripcion': 'Nombre'}
            return _handle_upload(request, Cie10, columns_map)
        elif upload_type == 'cups':
            if is_csv:
                columns_map = {'codigo': 0, 'descripcion': 1}
            else:
                columns_map = {'codigo': 'Codigo', 'descripcion': 'Nombre'}
            return _handle_upload(request, Cups, columns_map)
            
    return render(request, 'dashboard/import.html')

def export_csv(request, entity):
    models_map = {
        'entidades': (Eps, ['codigo', 'nombre', 'nit', 'regimen']),
        'cie10': (Cie10, ['codigo', 'descripcion', 'version', 'version_fecha']),
        'cups': (Cups, ['codigo', 'descripcion', 'version', 'version_fecha'])
    }
    
    if entity not in models_map:
        return HttpResponse("Entidad no encontrada", status=404)
        
    model, fields = models_map[entity]
    
    response = HttpResponse(content_type='text/csv')
    
    if entity in ['cie10', 'cups']:
        from datetime import datetime
        current_year = datetime.now().year
        filename = f"{entity}_{current_year}.csv"
        write_header = False
    else:
        filename = f"{entity}.csv"
        write_header = True
        
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response, delimiter=';')
    
    if write_header:
        writer.writerow(fields)
    
    for obj in model.objects.all().iterator():
        writer.writerow([getattr(obj, field) for field in fields])
        
    return response

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_index')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido de nuevo, {user.username}!')
            return redirect('dashboard_index')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
        
    return render(request, 'dashboard/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('dashboard_index')
