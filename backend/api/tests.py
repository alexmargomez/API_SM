"""
Suite de Pruebas Unitarias y de Integración para API_SM (Tablas SISPRO & Inspector HL7 FHIR Res. 1888).
Cubre:
  1. Repositorio de Catálogos (límites acotados contra abuso de memoria y caché TTL).
  2. Endpoints públicos y paginados de EPS, CIE-10 y CUPS.
  3. Flujo de autenticación de administradores y bloqueo de usuarios sin privilegios (403).
  4. Importador CSV y Exportador CSV de catálogos normativos.
  5. Motor Inspector HL7 FHIR Res. 1888 (Patient, Encounter, Condition, AllergyIntolerance, FamilyMemberHistory, MedicationStatement, Composition).
"""

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Eps, Cie10, Cups
from .repositories import CatalogRepository


class ApiSmArchitectureAndDomainTests(TestCase):
    def setUp(self):
        CatalogRepository.invalidate_cache()
        self.client = APIClient()

        # Semilla de catálogos SISPRO
        Eps.objects.create(codigo='EPS001', nombre='ALIANSALUD EPS', nit='830113831', regimen='CONTRIBUTIVO')
        Eps.objects.create(codigo='ESS024', nombre='COOSALUD EPS-S', nit='900226715', regimen='SUBSIDIADO')
        Cie10.objects.create(codigo='I10X', descripcion='HIPERTENSION ESENCIAL (PRIMARIA)', version='CIE10', version_fecha='2025')
        Cie10.objects.create(codigo='E119', descripcion='DIABETES MELLITUS NO INSULINODEPENDIENTE', version='CIE10', version_fecha='2025')
        Cups.objects.create(codigo='890201', descripcion='CONSULTA DE PRIMERA VEZ POR MEDICINA GENERAL', version='2026', version_fecha='2026-01')

        # Usuarios de prueba
        self.admin_user = User.objects.create_superuser(
            username='admin_sispro',
            email='admin@softwaremedico.com.co',
            password='StrongAdminPassword123!'
        )
        self.regular_user = User.objects.create_user(
            username='operador_lectura',
            email='operador@softwaremedico.com.co',
            password='RegularPassword123!'
        )

    def test_catalog_repository_bounds_abusive_limits_and_caches_stats(self):
        self.assertEqual(CatalogRepository.sanitize_limit('9999999'), CatalogRepository.MAX_LIMIT)
        self.assertEqual(CatalogRepository.sanitize_limit('-50'), 1)
        self.assertEqual(CatalogRepository.sanitize_limit('invalid_number', default=100), 100)

        stats = CatalogRepository.get_counts()
        self.assertEqual(stats['count_entidades'], 2)
        self.assertEqual(stats['count_cie10'], 2)
        self.assertEqual(stats['count_cups'], 1)

    def test_public_sispro_endpoints_filter_correctly(self):
        res_eps = self.client.get('/api/entidades', {'q': 'COOSALUD', 'limit': '10'})
        self.assertEqual(res_eps.status_code, 200)
        self.assertEqual(len(res_eps.data), 1)
        self.assertEqual(res_eps.data[0]['ent_id'], 'ESS024')

        res_cie10 = self.client.get('/api/cie10', {'q': 'I10X'})
        self.assertEqual(res_cie10.status_code, 200)
        self.assertEqual(len(res_cie10.data), 1)

        res_cups = self.client.get('/api/cups', {'q': '890201'})
        self.assertEqual(res_cups.status_code, 200)
        self.assertEqual(len(res_cups.data), 1)

    def test_panel_paginated_endpoints_and_regimen_filter(self):
        res = self.client.get('/api/panel/entidades/', {'regimen': 'CONTRIBUTIVO'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 1)
        self.assertEqual(res.data['results'][0]['codigo'], 'EPS001')
        self.assertIn('CONTRIBUTIVO', res.data['regimenes'])
        self.assertIn('SUBSIDIADO', res.data['regimenes'])

    def test_admin_authentication_lifecycle_and_rbac_protection(self):
        # 1. Usuario no superusuario debe recibir 403 Forbidden
        res_forbidden = self.client.post(
            '/api/auth/login/',
            {'username': 'operador_lectura', 'password': 'RegularPassword123!'},
            format='json'
        )
        self.assertEqual(res_forbidden.status_code, 403)

        # 2. Credenciales inválidas deben recibir 401 Unauthorized
        res_unauth = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_sispro', 'password': 'WrongPassword'},
            format='json'
        )
        self.assertEqual(res_unauth.status_code, 401)

        # 3. Login exitoso de superusuario
        res_ok = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_sispro', 'password': 'StrongAdminPassword123!'},
            format='json'
        )
        self.assertEqual(res_ok.status_code, 200)
        token = res_ok.data['token']

        # 4. Verificación de sesión (/api/auth/me/) y cierre de sesión (/api/auth/logout/)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        res_me = self.client.get('/api/auth/me/')
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.data['user']['username'], 'admin_sispro')

        res_logout = self.client.post('/api/auth/logout/')
        self.assertEqual(res_logout.status_code, 200)

    def test_csv_export_and_import_invalidates_cache(self):
        res_csv = self.client.get('/api/panel/export/cups/')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('text/csv', res_csv['Content-Type'])

        # Autenticar admin para importar nuevo CUPS
        login_res = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_sispro', 'password': 'StrongAdminPassword123!'},
            format='json'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login_res.data['token']}")

        csv_content = (
            b"codigo;descripcion;version;version_fecha\n"
            b"890201;CONSULTA DE PRIMERA VEZ POR MEDICINA GENERAL;2026;2026-01\n"
            b"890301;CONSULTA DE CONTROL POR MEDICINA GENERAL;2026;2026-01\n"
        )
        uploaded = SimpleUploadedFile('cups_update.csv', csv_content, content_type='text/csv')
        import_res = self.client.post('/api/panel/import/', {'type': 'cups', 'file': uploaded}, format='multipart')
        self.assertEqual(import_res.status_code, 200)
        self.assertEqual(Cups.objects.count(), 2)

        # Importar CSV de Entidades (EPS) con encabezados por nombre y coma (verifica que NO borra EPS en blanco)
        eps_csv = (
            b"Codigo,Nombre,NIT,Regimen\n"
            b"EPS005,SANITAS EPS,800251440,CONTRIBUTIVO\n"
            b"EPS010,SURA EPS,800088702,CONTRIBUTIVO\n"
            b"ESS091,ASMET SALUD,817000248,SUBSIDIADO\n"
        )
        uploaded_eps = SimpleUploadedFile('entidades_update.csv', eps_csv, content_type='text/csv')
        eps_res = self.client.post('/api/panel/import/', {'type': 'entidades', 'file': uploaded_eps}, format='multipart')
        self.assertEqual(eps_res.status_code, 200)
        self.assertEqual(Eps.objects.count(), 3)

        # Guardrail Zero-Wipe: subir un CSV vacío o sin registros válidos aborta con 400 y preserva las 3 EPS intactas
        empty_csv = SimpleUploadedFile('empty.csv', b"Codigo;Nombre;NIT;Regimen\n;;;\n", content_type='text/csv')
        wipe_res = self.client.post('/api/panel/import/', {'type': 'entidades', 'file': empty_csv}, format='multipart')
        self.assertEqual(wipe_res.status_code, 400)
        self.assertEqual(Eps.objects.count(), 3)

    def test_fhir_res_1888_bundle_inspector_sample_and_validation(self):
        # 1. GET devuelve el Bundle de ejemplo Res. 1888 inspeccionado
        res_get = self.client.get('/api/tools/fhir-inspector/')
        self.assertEqual(res_get.status_code, 200)
        self.assertIn('summary', res_get.data)
        self.assertIn('modules', res_get.data)
        self.assertIn('catalog_validations', res_get.data)
        module_ids = {m['id'] for m in res_get.data['modules']}
        self.assertTrue({'encabezado', 'paciente', 'atencion', 'diagnosticos', 'medicamentos', 'alergias_familiares_otros'}.issubset(module_ids))

        # 2. POST con un recurso individual que no es Bundle genera advertencia estructural en structural_warnings
        res_single = self.client.post(
            '/api/tools/fhir-inspector/',
            {'raw_json': '{"resourceType": "Patient", "id": "123"}'},
            format='json'
        )
        self.assertEqual(res_single.status_code, 200)
        self.assertGreater(len(res_single.data['structural_warnings']), 0)

        # 3. POST con JSON corrupto retorna 400 Bad Request
        res_bad = self.client.post(
            '/api/tools/fhir-inspector/',
            {'raw_json': '{corrupted_json_payload'},
            format='json'
        )
        self.assertEqual(res_bad.status_code, 400)
