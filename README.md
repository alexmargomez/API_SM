# 🏥 API_SM — Motor Central de Catálogos Normativos en Salud (CUPS, CIE-10, EPS) & Inspector FHIR Res. 1888 (IHCE)

**API_SM** es una plataforma centralizada de microservicios y panel administrativo **SPA (Vue 3 + Django REST Framework + MariaDB 11)** diseñada para proveer catálogos normativos oficiales del sector salud en Colombia (**CUPS**, **CIE-10** y **Entidades / EPS**), homologación masiva por versiones y un **Inspector / Traductor Clínico de Bundles HL7 FHIR R4 (Resolución 1888 / IHCE Minsalud)** con validación cruzada en lote contra la base de datos oficial.

![Python 3.11](https://img.shields.io/badge/Python-3.11_Slim-3776AB?logo=python&logoColor=white)
![Django 4.2 LTS](https://img.shields.io/badge/Django-4.2_LTS_%2B_DRF-092E20?logo=django&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue_3-Composition_API_%2B_Pinia-4FC08D?logo=vuedotjs&logoColor=white)
![Vite 5](https://img.shields.io/badge/Vite-5.x_SPA-646CFF?logo=vite&logoColor=white)
![MariaDB 11](https://img.shields.io/badge/MariaDB-11_Optimized-003545?logo=mariadb&logoColor=white)
![HL7 FHIR R4](https://img.shields.io/badge/HL7_FHIR_R4-Res._1888_%2F_IHCE_Colombia-E11D48)
![Docker Compose](https://img.shields.io/badge/Docker-Multi--Container-2496ED?logo=docker&logoColor=white)
![ALpanel Ready](https://img.shields.io/badge/ALpanel-3--Port_Standard_Ready-8A2BE2)

---

## 🚀 ¿Qué hace único a API_SM?

A diferencia de repositorios estáticos o scripts monolíticos que mezclan HTML dentro de vistas de Python, **API_SM** implementa una arquitectura **Monorepo Multicontenedor 100% desacoplada** con herramientas especializadas para interoperabilidad clínica:

1. **🩺 Inspector y Traductor Clínico de Bundles FHIR R4 (Resolución 1888 / IHCE Ministerio de Salud):**
   - **Auto-detección inteligente de los 4 tipos de RDA oficiales:**
     - `RDA de Paciente (Antecedentes Clínicos)`
     - `RDA de Consulta Externa`
     - `RDA de Urgencias`
     - `RDA de Hospitalización`
   - **Traducción completa a lenguaje clínico humano (8 pestañas estructuradas):**
     - **👤 Paciente (`Patient`):** Priorización estricta del estándar colombiano (`ColombianPersonIdentifier`: `CC`, `TI`, `CE`, `DE`, `PA`, `RC`, `MS`, `AS`, `CN`, `PE`, `PT`) sobre el código genérico HL7 `v2-0203` (`PN`), nombres desglosados, sexo biológico, identidad de género, fecha de nacimiento con cálculo de edad, nacionalidad, municipio/país de residencia, zona territorial y teléfono.
     - **🏥 Encuentro / Atención (`Encounter`):** Modalidad de atención, clasificación, vía de ingreso, causa o motivo de atención, triage, estado y periodo de la atención.
     - **🏢 Prestador e IPS / EPS (`Organization` + `Practitioner` + `Location`):** Identificación tributaria (`NIT`), código de habilitación REPS, ubicación física, aseguradora/administradora (`EAPB`) y profesionales de salud intervinientes.
     - **🧬 Antecedentes Clínicos Completos (`AllergyIntolerance`, `FamilyMemberHistory`, `MedicationStatement`, `ConditionStatementRDA`):**
       - *Alergias:* Estado clínico (`Active`/`Inactive`), **Estado de verificación** (`Confirmed`/`Unconfirmed`), Tipo de alergia (`Alergia`/`Intolerancia`), Código y Nombre del alergeno.
       - *Familiares:* Estado del antecedente (`Completed`), Parentesco (`FTH`, `MTH`, etc.), Diagnóstico (`CIE-10`) y Descripción.
       - *Farmacológicos:* Estado de la declaración del medicamento, Código `MipresINN` / `DCI`, Nombre del medicamento y Dosificación (`dosage.text`).
       - *Patológicos:* Condiciones previas y comorbilidades reportadas.
     - **🔬 Diagnósticos (`Condition` + `Encounter.diagnosis`):** Clasificación de diagnósticos de ingreso, principales, relacionados y de egreso con su rol, tipo y confirmación.
     - **💉 Procedimientos, Medicamentos e Incapacidades (`Procedure`, `MedicationRequest`, `MedicationAdministration`, `Observation`, `ServiceRequest`):** Cruce de procedimientos `CUPS`, prescripciones, administraciones de medicamentos, signos vitales/antropometría y órdenes médicas.
     - **📑 Documento Clínico (`Composition` + `DocumentReference`):** Metadatos del RDA, autor principal, custodio, nivel de confidencialidad, **eventos clínicos del acto (`Composition.event`)**, secciones estructuradas y anexos PDF/Base64.
     - **✅ Cruce Normativo en Lote contra Base de Datos Oficial (`API_SM`):** Extrae todos los códigos `CIE-10`, `CUPS` y `EPS` presentes en el Bundle JSON y los valida en una sola consulta batch contra MariaDB, indicando si el código existe, su nombre oficial en el catálogo vigente o si presenta discrepancias.

2. **⚡ Motor de Consultas REST de Alta Velocidad (Retrocompatible con Sistemas HIS / HCE Legacy):**
   - Endpoints públicos `/api/entidades`, `/api/cie10` y `/api/cups` optimizados para integrarse de forma transparente con sistemas de Historia Clínica Electrónica (Symfony 1.4, Laravel, Node.js, etc.).
   - Búsqueda simultánea por código exacto o coincidencia parcial de descripción/nombre, filtrado por versión normativa (`Año 2024`, `Año 2025`, `Año 2026`, etc.) y paginación configurable.

3. **📥 Importador Masivo Inteligente (Excel `.xlsx` / `.xls` y `.csv`) + Exportador CSV en 1 Clic:**
   - Procesamiento vectorizado con `pandas` + `openpyxl` capaz de insertar o actualizar miles de registros de **CUPS**, **CIE-10** y **EPS** mediante operaciones por lotes (`bulk_create` / `update_conflicts`).
   - Detección automática de columnas, asignación de etiquetas de versión (`version` y `version_fecha`) y descarga directa del catálogo filtrado en formato `.csv` compatible con Excel (UTF-8 con BOM).

4. **🧱 Arquitectura Monorepo Desacoplada Multicontenedor (`Frontend` + `Backend` + `MariaDB 11`):**
   - **Frontend (`frontend/`):** SPA reactiva en **Vue 3 (`<script setup>`) + Vue Router 4 + Pinia + Vite 5**, con diseño moderno oscuro/claro, barra lateral colapsable y componentes reutilizables.
   - **Backend (`backend/`):** API pura en **Django 4.2 LTS + Django REST Framework + Gunicorn**, separando controladores (`views.py`), serializadores (`serializers.py`) y capa de servicios (`services/fhir_inspector.py`, `services/importer.py`, `services/exporter.py`).
   - **Base de Datos (`db`):** Contenedor **MariaDB 11** afinado para bajo consumo de memoria (`innodb-buffer-pool-size=64M`, `performance-schema=OFF`) con *healthcheck* nativo antes de iniciar las migraciones de Django.

---

## 📦 Instalación y Despliegue (Local y en VPS con ALpanel)

### 1. Clonar el repositorio y configurar `.env`
```bash
git clone https://github.com/alexmargomez/API_SM.git
cd API_SM
cp .env.example .env
```

### 2. Ajustar las variables de entorno (`.env`)
Edita el archivo `.env` según tu entorno local o de producción:
```ini
# ==========================================
# Variables de Entorno - API_SM (Docker Compose)
# ==========================================

# 1. Puertos Expuestos (Sincronizados automáticamente por ALpanel)
BACKEND_PORT=8000
FRONTEND_PORT=5174
DB_EXTERNAL_PORT=3307

# 2. Claves de Django (Backend)
SECRET_KEY=poner_aqui_clave_secreta_django_segura
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=http://localhost,https://localhost,http://localhost:5174

# 3. Claves de Base de Datos (MariaDB 11)
MARIADB_DATABASE=api_sm_db
MARIADB_USER=api_user
MARIADB_PASSWORD=api_password
MARIADB_ROOT_PASSWORD=api_root_password

DB_NAME=api_sm_db
DB_USER=api_user
DB_PASSWORD=api_password
DB_HOST=db
DB_PORT=3306

# 4. Frontend (Vue 3 + Vite)
VITE_API_URL=/api
VITE_BACKEND_PROXY=http://backend:8000
```

### 3. Levantar los 3 contenedores con Docker Compose
```bash
docker compose up -d --build
```

Al iniciar, el contenedor `api_sm_django` esperará a que `api_sm_mariadb` pase el `healthcheck`, ejecutará automáticamente `python manage.py makemigrations && python manage.py migrate` y levantará el servidor **Gunicorn**.

- **Panel Administrativo SPA (Vue 3):** `http://localhost:5174`
- **API REST Backend (Django):** `http://localhost:8000/api/`
- **Base de Datos MariaDB (Puerto Externo):** `localhost:3307`

### 4. Crear un superusuario administrativo (Primera vez)
```bash
docker exec -it api_sm_django python manage.py createsuperuser
```

---

## 🔌 Compatibilidad Nativa con ALpanel (Estándar de 3 Variables de Puerto)

**API_SM** cumple al 100% con la especificación multicontenedor de **ALpanel** para despliegues automatizados en servidores VPS:

| Variable en `.env` | Contenedor Docker | Función en ALpanel |
| :--- | :--- | :--- |
| **`FRONTEND_PORT`** | `api_sm_frontend` | **Puerto del Frontend Vue 3 (`5174`).** Se sincroniza automáticamente con el **Frontend Target** configurado en la pestaña *Dominios & SSL* de ALpanel. |
| **`BACKEND_PORT`** | `api_sm_django` | **Puerto del Backend Django/Gunicorn (`8000`).** Se sincroniza con el **Backend Target (`/api/*`)** y actualiza automáticamente `VITE_BACKEND_PROXY`. |
| **`DB_EXTERNAL_PORT`** | `api_sm_mariadb` | **Puerto Externo SQL (`3307`).** ALpanel verifica los puertos libres del VPS y auto-asigna un puerto disponible sin colisionar con otros proyectos. |
| **`ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`** | `api_sm_django` | ALpanel inyecta automáticamente el dominio HTTPS real al asignarlo en *Dominios & SSL*, manteniendo el repositorio libre de dominios o IPs quemadas. |

### 🔄 Flujo de Ramas y Despliegue Continuo
- **`develop`:** Rama activa de desarrollo e integración de nuevas funcionalidades.
- **`main`:** Rama estable de producción. Una vez probado en `develop`, se realiza el *Merge Pull Request* hacia `main` en GitHub y se despliega en 1 clic desde **ALpanel** usando **`Git Pull`** + **`Restart Docker`** (o **`Rebuild`** preservando intactos los datos de MariaDB).

---

## 🗂️ Estructura de Carpetas del Monorepo (`backend/` + `frontend/`)

```text
API_SM/
├── docker-compose.yml                       # 🐳 Orquestación de los 3 servicios (db, backend, frontend) + red bridge y volúmenes
├── .env.example                             # 📋 Plantilla limpia de variables de entorno (compatible con ALpanel)
│
├── backend/                                 # ⚙️ BACKEND API REST (Python 3.11 + Django 4.2 + DRF + Gunicorn)
│   ├── Dockerfile                           # Imagen ligera python:3.11-slim con dependencias de compilación MySQL
│   ├── manage.py                            # CLI administrativo de Django
│   ├── requirements.txt                     # Dependencias Python (Django, DRF, corsheaders, mysqlclient, pandas, openpyxl, gunicorn)
│   ├── core/                                # 🏛️ Configuración central del proyecto Django
│   │   ├── settings.py                      # Configuración dinámica vía variables de entorno (.env), CORS, CSRF y MariaDB
│   │   ├── urls.py                          # Enrutador raíz (/admin/ y /api/)
│   │   ├── wsgi.py                          # Punto de entrada WSGI para Gunicorn en producción
│   │   └── asgi.py                          # Punto de entrada ASGI
│   └── api/                                 # 📦 Aplicación principal de catálogos normativos y herramientas clínicas
│       ├── models.py                        # Modelos ORM: Eps (codigo, nombre, nit, regimen), Cie10 y Cups (versionados)
│       ├── serializers.py                   # Serializadores Django REST Framework
│       ├── views.py                         # Controladores REST (Endpoints públicos, Panel SPA, Auth y FHIR Inspector)
│       ├── urls.py                          # Definición de rutas bajo el prefijo /api/
│       └── services/                        # 🧠 CAPA DE SERVICIOS DE DOMINIO (Lógica desacoplada de las vistas HTTP)
│           ├── fhir_inspector.py            # Motor traductor de Bundles HL7 FHIR R4 (Res. 1888 / IHCE) + validación DB en lote
│           ├── importer.py                  # Procesador masivo de archivos Excel (.xlsx/.xls) y CSV con pandas
│           └── exporter.py                  # Generador de descargas CSV en streaming con codificación UTF-8-SIG
│
└── frontend/                                # 🎨 FRONTEND SPA (Vue 3 Composition API + Pinia + Vue Router 4 + Vite 5)
    ├── Dockerfile                           # Contenedor Node.js con servidor Vite y proxy inverso dinámico hacia backend
    ├── package.json                         # Dependencias del cliente (vue, vue-router, pinia, vite)
    ├── vite.config.js                       # Configuración de Vite y proxy automático de /api -> VITE_BACKEND_PROXY
    ├── index.html                           # Plantilla raíz de la SPA
    └── src/
        ├── main.js                          # Inicialización de Vue 3, Pinia y Vue Router
        ├── App.vue                          # Layout maestro con Sidebar reactivo y área de trabajo dinámica
        ├── router/
        │   └── index.js                     # Definición de rutas SPA y guardias de navegación (requiresAuth)
        ├── stores/
        │   └── auth.js                      # Store Pinia para sesión de usuario, login/logout y verificación /api/auth/me/
        ├── services/
        │   └── api.js                       # Cliente HTTP centralizado (fetch wrapper con credenciales y manejo de errores)
        ├── components/                      # 🧩 Componentes UI reutilizables
        │   ├── SidebarNav.vue               # Menú lateral con navegación categorizada y estado de sesión
        │   ├── SearchFilterBar.vue          # Barra de búsqueda en vivo + selector de versión + exportación CSV
        │   └── PaginationBar.vue            # Paginador reactivo con control de página y conteo de registros
        └── views/                           # 🖥️ Vistas principales de la aplicación
            ├── DashboardView.vue            # Panel de métricas globales (totales CUPS, CIE-10, EPS y desglose por versión)
            ├── EntidadesView.vue            # Explorador y buscador de Entidades / Administradoras (EPS)
            ├── Cie10View.vue                # Explorador normativo de diagnósticos CIE-10 con filtro por versión
            ├── CupsView.vue                 # Explorador normativo de procedimientos CUPS con filtro por versión
            ├── FhirInspectorView.vue        # 🩺 Inspector / Traductor interactivo de Bundles FHIR Res. 1888 (8 módulos + drag & drop)
            ├── ImportView.vue               # Consola de carga masiva Excel/CSV (protegida por autenticación)
            ├── DocsView.vue                 # Documentación interactiva de los endpoints de la API con ejemplos cURL/JSON
            └── LoginView.vue                # Vista de inicio de sesión administrativo
```

---

## 📡 Referencia de Endpoints de la API REST (`/api/`)

### 1. Endpoints Públicos de Integración Externa (HCE / HIS)
Diseñados para consumo directo desde sistemas externos sin requerir sesión del panel:

| Método | Endpoint | Parámetros Query (`GET`) | Descripción |
| :--- | :--- | :--- | :--- |
| **`GET`** | `/api/entidades` | `q` *(búsqueda)*, `codigo`, `regimen`, `limit` | Consulta de Entidades / Administradoras (EPS) por código de habilitación, NIT o nombre. |
| **`GET`** | `/api/cie10` | `q` *(búsqueda)*, `codigo`, `version`, `limit` | Consulta de diagnósticos **CIE-10** por código exacto o texto descriptivo y versión normativa. |
| **`GET`** | `/api/cups` | `q` *(búsqueda)*, `codigo`, `version`, `limit` | Consulta de procedimientos **CUPS** por código exacto o descripción y versión normativa. |

#### Ejemplo de consumo con `cURL`:
```bash
# Buscar procedimientos CUPS que coincidan con "890201" (Consulta de primera vez)
curl -X GET "http://localhost:8000/api/cups?q=890201&limit=10"
```

---

### 2. Endpoints del Panel Administrativo SPA y Herramientas Clínicas

| Método | Endpoint | Autenticación | Descripción |
| :--- | :--- | :--- | :--- |
| **`GET`** | `/api/panel/stats/` | Pública (Lectura) | Métricas globales de registros (`EPS`, `CIE-10`, `CUPS`) y agrupación histórica por versiones. |
| **`GET`** | `/api/panel/entidades/` | Pública (Lectura) | Listado paginado de EPS con filtros de búsqueda y régimen. |
| **`GET`** | `/api/panel/cie10/` | Pública (Lectura) | Listado paginado de CIE-10 con selector de versión y búsqueda instantánea. |
| **`GET`** | `/api/panel/cups/` | Pública (Lectura) | Listado paginado de CUPS con selector de versión y búsqueda instantánea. |
| **`GET`** | `/api/panel/export/<entity>/` | Pública (Lectura) | Descarga directa en `.csv` (`entidades`, `cie10` o `cups`) aplicando los filtros activos. |
| **`POST`** | `/api/tools/fhir-inspector/` | Pública (Utilidad) | Recibe un `bundle` FHIR R4 (JSON), lo traduce en 8 secciones clínicas y valida `CIE-10`, `CUPS` y `EPS` contra la base de datos. |
| **`POST`** | `/api/panel/import/` | 🔒 Requiere Login | Importación masiva de archivos `.xlsx`, `.xls` o `.csv` hacia `entidades`, `cie10` o `cups`. |
| **`POST`** | `/api/auth/login/` | Pública | Inicio de sesión administrativo en el panel SPA. |
| **`POST`** | `/api/auth/logout/` | 🔒 Requiere Login | Cierre de sesión activa. |
| **`GET`** | `/api/auth/me/` | Pública | Verifica el estado de autenticación actual del usuario en la SPA. |

---

## 🩺 Detalle Técnico del Inspector / Traductor FHIR R4 (Resolución 1888 / IHCE)

El servicio [`backend/api/services/fhir_inspector.py`](backend/api/services/fhir_inspector.py) procesa cualquier `Bundle` transaccional o documental bajo los lineamientos técnicos de la **Resolución 1888 de 2025 (Ministerio de Salud y Protección Social de Colombia)**:

1. **Priorización de Sistemas de Codificación Nacionales (`CodeSystem` Minsalud):**
   - En recursos `Patient`, `Practitioner`, `RelatedPerson` y `Organization`, prioriza automáticamente los sistemas oficiales `ColombianPersonIdentifier`, `ColombianOrganizationIdentifiers` y `ColombianDocumentTypes` (`CC`, `TI`, `CE`, `DE`, `PA`, `NIT`, etc.) por encima del tipo genérico internacional `http://terminology.hl7.org/CodeSystem/v2-0203` (`PN` / `TAX`), mostrando el identificador compuesto tal como lo exige el validador del Ministerio (ej. `DE-095305827-14`).
2. **Desglose Integral de Antecedentes Clínicos (`RDA de Paciente` y `RDA de Encuentros`):**
   - **Alergias (`AllergyIntolerance`):** Muestra `Estado clínico` (`clinicalStatus`), `Estado de verificación` (`verificationStatus`), `Tipo de alergia` (`type` / `category`), `Código` y `Nombre del alergeno`.
   - **Antecedentes Familiares (`FamilyMemberHistory`):** Muestra `Estado del antecedente familiar` (`status`), `Parentesco` (`relationship`), `Diagnóstico` (`condition.code` CIE-10) y `Descripción`.
   - **Antecedentes Farmacológicos (`MedicationStatement`):** Muestra `Estado de la declaración del medicamento` (`status`), código `MipresINN` / `DCI`, `Medicamento` y `Dosificación` (`dosage.text`).
3. **Auditoría Cruzada contra Catálogos Locales:**
   - Todos los códigos detectados en el JSON se consultan en bloque (`__in`) contra las tablas `Cie10`, `Cups` y `Eps` de **API_SM**, generando un semáforo de conformidad (`✔ Encontrado en BD` vs `⚠ No registrado en catálogo local`) junto con el porcentaje global de coincidencia normativa.
