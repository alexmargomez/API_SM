<script setup>
import { ref, computed } from 'vue'
import { apiService } from '../services/api'

const rawJsonInput = ref('')
const loading = ref(false)
const errorMsg = ref('')
const result = ref(null)
const selectedModuleId = ref('all')
const validationFilter = ref('all')
const expandedRawJson = ref({})
const showStructuredJsonModal = ref(false)
const copiedReport = ref(false)
const fileInputRef = ref(null)

const filteredModules = computed(() => {
  if (!result.value?.modules) return []
  if (selectedModuleId.value === 'all') return result.value.modules
  return result.value.modules.filter((m) => m.id === selectedModuleId.value)
})

const filteredMandatoryValidations = computed(() => {
  const list = result.value?.mandatory_validations || []
  if (validationFilter.value === 'all') return list
  return list.filter((item) => item.status === validationFilter.value)
})

function formatExplanationHtml(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-dark">$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}

async function runInspection() {
  errorMsg.value = ''
  if (!rawJsonInput.value.trim()) {
    errorMsg.value = 'Por favor pega un JSON de Bundle FHIR o sube un archivo .json para procesarlo en el servidor Python.'
    return
  }

  loading.value = true
  try {
    const res = await apiService.inspectFhirBundle(rawJsonInput.value)
    result.value = res
    selectedModuleId.value = 'all'
    validationFilter.value = (res.summary?.mandatory_failed_count || 0) > 0 ? 'missing' : 'all'
    expandedRawJson.value = {}
  } catch (err) {
    errorMsg.value = err.message || 'No se pudo procesar el JSON FHIR en el servidor.'
  } finally {
    loading.value = false
  }
}

async function loadSampleBundle() {
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await apiService.getFhirSampleAnalysis()
    if (res.sample_raw_json) {
      rawJsonInput.value = res.sample_raw_json
    }
    result.value = res
    selectedModuleId.value = 'all'
    validationFilter.value = 'all'
    expandedRawJson.value = {}
  } catch (err) {
    errorMsg.value = err.message || 'No se pudo cargar el ejemplo desde el backend Python.'
  } finally {
    loading.value = false
  }
}

function clearAll() {
  rawJsonInput.value = ''
  result.value = null
  errorMsg.value = ''
  validationFilter.value = 'all'
  expandedRawJson.value = {}
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

async function handleFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await apiService.inspectFhirFile(file)
    result.value = res
    selectedModuleId.value = 'all'
    validationFilter.value = (res.summary?.mandatory_failed_count || 0) > 0 ? 'missing' : 'all'
    expandedRawJson.value = {}
  } catch (err) {
    errorMsg.value = err.message || 'Error al procesar el archivo en el backend Python.'
  } finally {
    loading.value = false
    event.target.value = ''
  }
}

function toggleRawItem(key) {
  expandedRawJson.value[key] = !expandedRawJson.value[key]
}

async function copyPlainTextReport() {
  if (!result.value?.plain_text_report) return
  try {
    await navigator.clipboard.writeText(result.value.plain_text_report)
    copiedReport.value = true
    setTimeout(() => {
      copiedReport.value = false
    }, 2500)
  } catch {
    // ignore
  }
}
</script>

<template>
  <div>
    <!-- Encabezado de la Herramienta -->
    <div class="glass-card mb-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
        <div>
          <span class="badge bg-primary bg-opacity-10 text-primary px-3 py-2 rounded-pill fw-semibold mb-2">
            <i class="fas fa-microscope me-1"></i> Procesamiento Backend Python • Res. 1888 / IHCE
          </span>
          <h2 class="fw-bold mb-1">Inspector y Validador de Estructura Obligatoria FHIR (Res. 1888)</h2>
          <p class="text-muted mb-0">
            Envía el JSON o archivo <code>.json</code> al motor de <strong>Python (Django)</strong> para traducir el
            RDA a lenguaje claro y <strong>verificar que todos los datos, códigos y bloques de estructura obligatorios se hayan construido en el FHIR</strong>
            (ya que cuando un código o dato es inválido en origen, no se construye en el FHIR).
          </p>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button
            type="button"
            class="btn btn-outline-primary fw-semibold rounded-3"
            :disabled="loading"
            @click="loadSampleBundle"
          >
            <i class="fas fa-magic me-1"></i> Probar Ejemplo RDA (Backend)
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary fw-semibold rounded-3"
            :disabled="loading"
            @click="triggerFileUpload"
          >
            <i class="fas fa-file-upload me-1"></i> Subir Archivo .json al Servidor
          </button>
          <input
            ref="fileInputRef"
            type="file"
            accept=".json,application/json,text/plain"
            class="d-none"
            @change="handleFileChange"
          />
          <button
            v-if="rawJsonInput || result"
            type="button"
            class="btn btn-light text-danger fw-semibold rounded-3"
            @click="clearAll"
          >
            <i class="fas fa-trash-alt me-1"></i> Limpiar
          </button>
        </div>
      </div>

      <!-- Editor de Entrada JSON -->
      <div class="mb-3">
        <label class="form-label fw-semibold text-secondary small text-uppercase">
          Pega aquí el JSON del Bundle FHIR (o sube directamente el archivo .json arriba)
        </label>
        <textarea
          v-model="rawJsonInput"
          rows="7"
          class="form-control font-monospace small"
          style="border-radius: 14px; background-color: #f8fafc; border: 1px solid #cbd5e1;"
          placeholder='Pega aquí el JSON del Bundle FHIR (ej. { "resourceType": "Bundle", "entry": [ ... ] })...'
        ></textarea>
      </div>

      <div v-if="errorMsg" class="alert alert-danger rounded-3 d-flex align-items-center gap-2 mb-3">
        <i class="fas fa-exclamation-triangle"></i>
        <span>{{ errorMsg }}</span>
      </div>

      <div class="d-flex justify-content-end">
        <button type="button" class="btn btn-premium px-4" :disabled="loading" @click="runInspection">
          <i class="fas" :class="loading ? 'fa-spinner fa-spin' : 'fa-bolt'"></i>
          <span class="ms-2">
            {{ loading ? 'Procesando en Python...' : 'Validar Estructura y Traducir RDA' }}
          </span>
        </button>
      </div>
    </div>

    <!-- Resultados del Análisis devueltos por Python -->
    <template v-if="result">
      <!-- 1. Semáforo de Resumen Ejecutivo -->
      <div class="glass-card mb-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
          <div>
            <h4 class="fw-bold mb-1">
              <i class="fas fa-clipboard-check text-primary me-2"></i>
              {{ result.summary.rda_type }}
            </h4>
            <p class="text-muted small mb-0">
              Fecha del RDA: <strong>{{ result.summary.rda_date }}</strong> •
              Total de recursos FHIR construidos: <strong>{{ result.summary.total_resources }}</strong>
            </p>
          </div>

          <div class="d-flex flex-wrap gap-2">
            <button
              type="button"
              class="btn btn-outline-dark rounded-3 px-3 py-2 fw-semibold"
              @click="showStructuredJsonModal = !showStructuredJsonModal"
            >
              <i class="fas fa-file-code me-1"></i>
              {{ showStructuredJsonModal ? 'Ocultar JSON Estructurado' : 'Ver JSON Estructurado (Python)' }}
            </button>
            <button
              type="button"
              class="btn btn-export px-3 py-2"
              @click="copyPlainTextReport"
            >
              <i class="fas" :class="copiedReport ? 'fa-check' : 'fa-copy'"></i>
              <span class="ms-2">
                {{ copiedReport ? '¡Reporte copiado!' : 'Copiar Reporte en Texto Legible' }}
              </span>
            </button>
          </div>
        </div>

        <!-- Vista opcional del JSON limpio devuelto por el backend Python -->
        <div v-if="showStructuredJsonModal" class="mb-3">
          <div class="small fw-bold text-secondary mb-1">
            Respuesta JSON ya traducida y estructurada por el backend Python (<code>POST /api/tools/fhir-inspector/</code>):
          </div>
          <pre
            class="p-3 rounded-4 bg-dark text-light small mb-0 overflow-auto"
            style="max-height: 360px;"
          ><code>{{ JSON.stringify({ summary: result.summary, mandatory_validations: result.mandatory_validations, catalog_validations: result.catalog_validations, modules: result.modules.map(m => ({ title: m.title, missing_alerts: m.missing_alerts, narrative: m.narrative, items: m.items.map(i => ({ title: i.title, fields: i.fields })) })) }, null, 2) }}</code></pre>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <div class="p-3 rounded-4 bg-light border h-100">
              <div class="text-muted small fw-semibold">Recursos Construidos en Bundle</div>
              <div class="fs-3 fw-bold text-primary">{{ result.summary.total_resources }}</div>
              <div class="d-flex flex-wrap gap-1 mt-1">
                <span
                  v-for="(count, rtype) in result.summary.resource_counts"
                  :key="rtype"
                  class="badge bg-white text-dark border small"
                >
                  {{ rtype }}: {{ count }}
                </span>
              </div>
            </div>
          </div>

          <div class="col-md-3">
            <div
              class="p-3 rounded-4 border h-100"
              :class="
                (result.summary.mandatory_failed_count || 0) > 0
                  ? 'bg-danger bg-opacity-10 border-danger border-opacity-25'
                  : 'bg-success bg-opacity-10 border-success border-opacity-25'
              "
            >
              <div
                class="small fw-semibold"
                :class="(result.summary.mandatory_failed_count || 0) > 0 ? 'text-danger' : 'text-success'"
              >
                Apartados Obligatorios Faltantes
              </div>
              <div
                class="fs-3 fw-bold"
                :class="(result.summary.mandatory_failed_count || 0) > 0 ? 'text-danger' : 'text-success'"
              >
                <i
                  class="fas me-1"
                  :class="(result.summary.mandatory_failed_count || 0) > 0 ? 'fa-exclamation-triangle' : 'fa-check-circle'"
                ></i>
                {{ result.summary.mandatory_failed_count ?? 0 }} faltante(s)
              </div>
              <div class="text-muted small">
                {{ result.summary.mandatory_passed_count ?? 0 }} de {{ result.summary.total_mandatory_checks ?? 0 }} apartados/datos obligatorios presentes
              </div>
            </div>
          </div>

          <div class="col-md-3">
            <div class="p-3 rounded-4 bg-success bg-opacity-10 border border-success border-opacity-25 h-100">
              <div class="text-success small fw-semibold">Códigos Válidos en BD (API SM)</div>
              <div class="fs-3 fw-bold text-success">
                <i class="fas fa-check-circle me-1"></i> {{ result.summary.valid_codes_count }}
              </div>
              <div class="text-muted small">
                De {{ result.summary.total_codes_checked }} código(s) construidos (CIE-10, CUPS, EPS)
              </div>
            </div>
          </div>

          <div class="col-md-3">
            <div
              class="p-3 rounded-4 border h-100"
              :class="
                (result.summary.invalid_codes_count || 0) > 0
                  ? 'bg-danger bg-opacity-10 border-danger border-opacity-25'
                  : 'bg-light'
              "
            >
              <div
                class="small fw-semibold"
                :class="(result.summary.invalid_codes_count || 0) > 0 ? 'text-danger' : 'text-muted'"
              >
                Códigos Inválidos en BD (API SM)
              </div>
              <div
                class="fs-3 fw-bold"
                :class="(result.summary.invalid_codes_count || 0) > 0 ? 'text-danger' : 'text-secondary'"
              >
                <i
                  class="fas me-1"
                  :class="(result.summary.invalid_codes_count || 0) > 0 ? 'fa-times-circle' : 'fa-shield-alt'"
                ></i>
                {{ result.summary.invalid_codes_count }}
              </div>
              <div class="text-muted small">
                {{
                  (result.summary.invalid_codes_count || 0) > 0
                    ? 'Códigos construidos que no existen en SISPRO'
                    : 'Todos los códigos construidos existen en BD'
                }}
              </div>
            </div>
          </div>
        </div>

        <!-- Alertas de Apartados Obligatorios Faltantes si existen -->
        <div
          v-if="result.structural_warnings && result.structural_warnings.length > 0"
          class="alert alert-danger rounded-4 mb-3 border-danger shadow-sm"
        >
          <h6 class="fw-bold mb-2">
            <i class="fas fa-exclamation-circle me-1"></i> ¡Atención! Faltan Apartados o Datos Obligatorios en el FHIR:
          </h6>
          <ul class="mb-0 small fw-semibold">
            <li v-for="(warn, wIdx) in result.structural_warnings" :key="wIdx" class="mb-1">
              {{ warn }}
            </li>
          </ul>
        </div>

        <!-- Tabla 1: Verificación de Apartados y Estructura Obligatoria Res. 1888 -->
        <div v-if="result.mandatory_validations && result.mandatory_validations.length > 0" class="mt-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <h6 class="fw-bold text-secondary text-uppercase small mb-0">
              <i class="fas fa-tasks me-1"></i> 1. Verificación de Apartados y Datos Obligatorios en el FHIR (Res. 1888 / IHCE)
            </h6>
            <div class="d-flex flex-wrap gap-1">
              <button
                type="button"
                class="btn btn-sm rounded-pill px-3 py-1 fw-semibold"
                :class="validationFilter === 'all' ? 'btn-dark' : 'btn-outline-secondary'"
                @click="validationFilter = 'all'"
              >
                Todos ({{ result.mandatory_validations.length }})
              </button>
              <button
                type="button"
                class="btn btn-sm rounded-pill px-3 py-1 fw-semibold"
                :class="validationFilter === 'missing' ? 'btn-danger' : 'btn-outline-danger'"
                @click="validationFilter = 'missing'"
              >
                <i class="fas fa-times-circle me-1"></i> Apartados / Datos Faltantes ({{ result.summary.mandatory_failed_count || 0 }})
              </button>
              <button
                type="button"
                class="btn btn-sm rounded-pill px-3 py-1 fw-semibold"
                :class="validationFilter === 'empty_section' ? 'btn-warning text-dark' : 'btn-outline-warning text-dark'"
                @click="validationFilter = 'empty_section'"
              >
                <i class="fas fa-folder-open me-1"></i> Secciones en 0 ({{ result.summary.empty_sections_count || 0 }})
              </button>
              <button
                type="button"
                class="btn btn-sm rounded-pill px-3 py-1 fw-semibold"
                :class="validationFilter === 'ok' ? 'btn-success' : 'btn-outline-success'"
                @click="validationFilter = 'ok'"
              >
                <i class="fas fa-check-circle me-1"></i> Presentes OK ({{ result.summary.mandatory_passed_count || 0 }})
              </button>
            </div>
          </div>

          <div class="table-responsive" style="max-height: 420px; overflow-y: auto;">
            <table class="table table-sm align-middle mb-0">
              <thead style="position: sticky; top: 0; background: #fff; z-index: 2;">
                <tr>
                  <th>Módulo RDA</th>
                  <th>Recurso FHIR</th>
                  <th>Apartado / Dato Obligatorio (Res. 1888)</th>
                  <th>Resultado en el JSON FHIR</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(mv, mIdx) in filteredMandatoryValidations"
                  :key="mIdx"
                  :class="mv.status === 'missing' ? 'table-danger' : ''"
                >
                  <td class="small fw-semibold text-secondary">{{ mv.module }}</td>
                  <td>
                    <span class="badge bg-dark font-monospace">{{ mv.resource }}</span>
                  </td>
                  <td class="fw-bold">{{ mv.field }}</td>
                  <td>
                    <span
                      :class="
                        mv.status === 'missing'
                          ? 'text-danger fw-bold'
                          : mv.status === 'empty_section'
                          ? 'text-warning-emphasis small'
                          : 'text-dark'
                      "
                    >
                      {{ mv.value || '—' }}
                    </span>
                  </td>
                  <td>
                    <span v-if="mv.status === 'ok'" class="badge bg-success">
                      <i class="fas fa-check me-1"></i> Presente
                    </span>
                    <span v-else-if="mv.status === 'empty_section'" class="badge bg-warning text-dark">
                      <i class="fas fa-exclamation-triangle me-1"></i> Sección Vacía (0)
                    </span>
                    <span v-else class="badge bg-danger">
                      <i class="fas fa-exclamation-circle me-1"></i>
                      {{ mv.is_entire_apartado ? '¡Falta Apartado Obligatorio!' : '¡Falta Dato Obligatorio!' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="filteredMandatoryValidations.length === 0">
                  <td colspan="5" class="text-center text-muted py-3 small">
                    No hay elementos para el filtro seleccionado.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tabla 2: Auditoría de Códigos Construidos contra Catálogos Oficiales de API_SM -->
        <div v-if="result.catalog_validations && result.catalog_validations.length > 0" class="mt-4 pt-3 border-top">
          <h6 class="fw-bold text-secondary text-uppercase small mb-2">
            <i class="fas fa-database me-1"></i> 2. Validación de Códigos Construidos contra Base de Datos SISPRO (API_SM)
          </h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th>Catálogo</th>
                  <th>Código en JSON</th>
                  <th>Nombre Enviado en el RDA</th>
                  <th>Estado en BD (API_SM)</th>
                  <th>Nombre Oficial en Base de Datos</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(cv, idx) in result.catalog_validations" :key="idx">
                  <td class="fw-semibold">{{ cv.catalog }}</td>
                  <td>
                    <code class="fw-bold px-2 py-1 rounded bg-light text-dark">{{ cv.code }}</code>
                  </td>
                  <td>{{ cv.sent_name || '—' }}</td>
                  <td>
                    <span v-if="cv.valid" class="badge bg-success">
                      <i class="fas fa-check me-1"></i> Válido en BD
                    </span>
                    <span v-else class="badge bg-danger">
                      <i class="fas fa-times me-1"></i> No existe en BD
                    </span>
                  </td>
                  <td :class="cv.valid ? 'text-dark' : 'text-danger fw-semibold'">
                    {{ cv.official_name }}
                    <span v-if="cv.extra" class="text-muted small d-block">{{ cv.extra }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 2. Barra de Filtro por Módulos en Español -->
      <div class="d-flex flex-wrap gap-2 mb-4">
        <button
          type="button"
          class="btn btn-sm rounded-pill px-3 py-2 fw-semibold"
          :class="selectedModuleId === 'all' ? 'btn-primary shadow-sm' : 'btn-light border'"
          @click="selectedModuleId = 'all'"
        >
          <i class="fas fa-layer-group me-1"></i> Todos los Módulos ({{ result.modules.length }})
        </button>
        <button
          v-for="mod in result.modules"
          :key="mod.id"
          type="button"
          class="btn btn-sm rounded-pill px-3 py-2 fw-semibold"
          :class="
            selectedModuleId === mod.id
              ? (mod.has_missing_apartados ? 'btn-danger shadow-sm' : 'btn-primary shadow-sm')
              : (mod.has_missing_apartados ? 'btn-outline-danger bg-danger bg-opacity-10 fw-bold' : 'btn-light border')
          "
          @click="selectedModuleId = mod.id"
        >
          <i :class="mod.fa_icon" class="me-1"></i>
          {{ mod.title }}
          <span
            v-if="mod.has_missing_apartados"
            class="badge rounded-pill bg-danger ms-1"
          >
            <i class="fas fa-exclamation-triangle me-1"></i> ¡Falta Apartado!
          </span>
          <span v-else class="badge rounded-pill ms-1" :class="mod.count > 0 ? 'bg-dark' : 'bg-secondary'">
            {{ mod.count }}
          </span>
        </button>
      </div>

      <!-- 3. Desglose de cada Módulo (Nombre Legible y Resultado al Frente) -->
      <div
        v-for="mod in filteredModules"
        :key="mod.id"
        class="glass-card mb-4"
        :class="mod.has_missing_apartados ? 'border border-danger border-2' : ''"
      >
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 border-bottom pb-3 mb-3">
          <div class="d-flex align-items-center gap-2">
            <span class="fs-4" :class="mod.has_missing_apartados ? 'text-danger' : `text-${mod.color}`">
              <i :class="mod.fa_icon"></i>
            </span>
            <h4 class="fw-bold mb-0">{{ mod.title }}</h4>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span
              v-if="mod.has_missing_apartados"
              class="badge rounded-pill bg-danger px-3 py-2"
            >
              <i class="fas fa-exclamation-circle me-1"></i> ¡Falta Apartado Obligatorio!
            </span>
            <span class="badge rounded-pill px-3 py-2" :class="`bg-${mod.color}`">
              {{ mod.count }} registro(s) en este módulo
            </span>
          </div>
        </div>

        <!-- Alerta Roja dentro del módulo si falta un apartado obligatorio (ej. falta CUPS en Consulta) -->
        <div
          v-if="mod.missing_alerts && mod.missing_alerts.length > 0"
          class="alert alert-danger rounded-4 border-danger mb-3"
        >
          <div class="fw-bold mb-1">
            <i class="fas fa-exclamation-triangle me-1"></i>
            ¡Falta apartado o estructura obligatoria en este módulo!
          </div>
          <ul class="mb-0 small fw-semibold">
            <li v-for="(mAlert, aIdx) in mod.missing_alerts" :key="aIdx">
              {{ mAlert }}
            </li>
          </ul>
        </div>

        <!-- Explicación narrativa en lenguaje entendible -->
        <div
          class="p-3 rounded-4 mb-3"
          style="background-color: #f8fafc; border-left: 4px solid #4f46e5;"
        >
          <div class="small text-uppercase fw-bold text-primary mb-1">
            <i class="fas fa-comment-medical me-1"></i> Traducción en lenguaje claro:
          </div>
          <div class="text-secondary" v-html="formatExplanationHtml(mod.narrative)"></div>
        </div>

        <!-- Tabla de cada registro con Nombre Legible a la izquierda y Resultado al frente -->
        <div v-if="mod.items && mod.items.length > 0" class="d-flex flex-column gap-3">
          <div
            v-for="(item, iIdx) in mod.items"
            :key="`${mod.id}-${iIdx}`"
            class="p-3 rounded-4 bg-white border shadow-sm"
          >
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
              <div>
                <h5 class="fw-bold text-dark mb-1">{{ item.title }}</h5>
                <div class="text-muted small">{{ item.subtitle }}</div>
              </div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge px-3 py-2" :class="`bg-${item.badge_type || 'secondary'}`">
                  {{ item.badge }}
                </span>
                <button
                  type="button"
                  class="btn btn-sm btn-outline-secondary rounded-pill"
                  @click="toggleRawItem(`${mod.id}-${iIdx}`)"
                >
                  <i class="fas fa-code me-1"></i>
                  {{ expandedRawJson[`${mod.id}-${iIdx}`] ? 'Ocultar bloque FHIR' : 'Ver bloque FHIR original' }}
                </button>
              </div>
            </div>

            <!-- Tabla Campo Legible -> Resultado al frente -->
            <div class="table-responsive">
              <table class="table table-sm table-bordered align-middle mb-0">
                <thead>
                  <tr>
                    <th style="width: 35%; background-color: #f8fafc;">Campo (Lenguaje Legible)</th>
                    <th style="width: 65%; background-color: #f8fafc;">Resultado en el RDA</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(field, fIdx) in item.fields" :key="fIdx">
                    <td class="fw-semibold text-secondary bg-light" style="width: 35%;">
                      {{ field.label }}
                    </td>
                    <td class="fw-semibold text-dark text-break" style="width: 65%;">
                      {{ field.value }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Visor colapsable del recurso JSON FHIR exacto -->
            <div v-if="expandedRawJson[`${mod.id}-${iIdx}`]" class="mt-3">
              <pre
                class="p-3 rounded-3 bg-dark text-light small mb-0 overflow-auto"
                style="max-height: 320px;"
              ><code>{{ JSON.stringify(item.raw_resource, null, 2) }}</code></pre>
            </div>
          </div>
        </div>

        <div v-else class="text-muted small fst-italic">
          Este Bundle no incluye registros construidos para este módulo.
        </div>
      </div>
    </template>
  </div>
</template>
