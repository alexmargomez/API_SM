<script setup>
import { ref, computed } from 'vue'
import { apiService } from '../services/api'

const rawJsonInput = ref('')
const loading = ref(false)
const errorMsg = ref('')
const result = ref(null)
const selectedModuleId = ref('all')
const expandedRawJson = ref({})
const showStructuredJsonModal = ref(false)
const copiedReport = ref(false)
const fileInputRef = ref(null)

const filteredModules = computed(() => {
  if (!result.value?.modules) return []
  if (selectedModuleId.value === 'all') return result.value.modules
  return result.value.modules.filter((m) => m.id === selectedModuleId.value)
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
          <h2 class="fw-bold mb-1">Inspector y Traductor de Bundles FHIR a Lenguaje Claro</h2>
          <p class="text-muted mb-0">
            Envía el JSON o archivo <code>.json</code> al motor de <strong>Python (Django)</strong> para que procese la
            estructura FHIR en el servidor, cruce los códigos contra MariaDB y devuelva cada módulo con
            <strong>nombres legibles y su resultado al frente</strong>.
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
            {{ loading ? 'Procesando en Python...' : 'Procesar y Traducir en Backend' }}
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
              Total de bloques FHIR procesados por Python: <strong>{{ result.summary.total_resources }}</strong>
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
          ><code>{{ JSON.stringify({ summary: result.summary, catalog_validations: result.catalog_validations, modules: result.modules.map(m => ({ title: m.title, narrative: m.narrative, items: m.items.map(i => ({ title: i.title, fields: i.fields })) })) }, null, 2) }}</code></pre>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <div class="p-3 rounded-4 bg-light border h-100">
              <div class="text-muted small fw-semibold">Recursos en el Bundle</div>
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
            <div class="p-3 rounded-4 bg-success bg-opacity-10 border border-success border-opacity-25 h-100">
              <div class="text-success small fw-semibold">Códigos Válidos en BD (API SM)</div>
              <div class="fs-3 fw-bold text-success">
                <i class="fas fa-check-circle me-1"></i> {{ result.summary.valid_codes_count }}
              </div>
              <div class="text-muted small">CIE-10, CUPS y EPS verificados</div>
            </div>
          </div>

          <div class="col-md-3">
            <div
              class="p-3 rounded-4 border h-100"
              :class="
                result.summary.invalid_codes_count > 0
                  ? 'bg-danger bg-opacity-10 border-danger border-opacity-25'
                  : 'bg-light'
              "
            >
              <div
                class="small fw-semibold"
                :class="result.summary.invalid_codes_count > 0 ? 'text-danger' : 'text-muted'"
              >
                Códigos No Encontrados
              </div>
              <div
                class="fs-3 fw-bold"
                :class="result.summary.invalid_codes_count > 0 ? 'text-danger' : 'text-secondary'"
              >
                <i
                  class="fas me-1"
                  :class="result.summary.invalid_codes_count > 0 ? 'fa-times-circle' : 'fa-shield-alt'"
                ></i>
                {{ result.summary.invalid_codes_count }}
              </div>
              <div class="text-muted small">
                {{
                  result.summary.invalid_codes_count > 0
                    ? 'Revisa la tabla de auditoría abajo'
                    : 'Todos los códigos existen en catálogo'
                }}
              </div>
            </div>
          </div>

          <div class="col-md-3">
            <div
              class="p-3 rounded-4 border h-100"
              :class="
                result.summary.structural_warnings_count > 0
                  ? 'bg-warning bg-opacity-10 border-warning border-opacity-25'
                  : 'bg-light'
              "
            >
              <div class="small fw-semibold text-muted">Alertas Estructurales FHIR</div>
              <div
                class="fs-3 fw-bold"
                :class="result.summary.structural_warnings_count > 0 ? 'text-warning' : 'text-secondary'"
              >
                <i class="fas fa-project-diagram me-1"></i>
                {{ result.summary.structural_warnings_count }}
              </div>
              <div class="text-muted small">Referencias #id y secciones RDA</div>
            </div>
          </div>
        </div>

        <!-- Alertas Estructurales si existen -->
        <div
          v-if="result.structural_warnings && result.structural_warnings.length > 0"
          class="alert alert-warning rounded-4 mb-3"
        >
          <h6 class="fw-bold mb-2">
            <i class="fas fa-exclamation-circle me-1"></i> Alertas de Estructura Detectadas en el JSON:
          </h6>
          <ul class="mb-0 small">
            <li v-for="(warn, wIdx) in result.structural_warnings" :key="wIdx">
              {{ warn }}
            </li>
          </ul>
        </div>

        <!-- Tabla de Cruce contra Catálogos Oficiales (CIE-10, CUPS, EPS) -->
        <div v-if="result.catalog_validations && result.catalog_validations.length > 0" class="mt-3">
          <h6 class="fw-bold text-secondary text-uppercase small mb-2">
            <i class="fas fa-database me-1"></i> Auditoría Automática de Códigos contra Base de Datos SISPRO (API SM)
          </h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th>Catálogo</th>
                  <th>Código Enviado</th>
                  <th>Nombre Enviado en el JSON</th>
                  <th>Nombre Oficial en Base de Datos (API SM)</th>
                  <th>Resultado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(cv, cIdx) in result.catalog_validations" :key="cIdx">
                  <td class="fw-semibold">{{ cv.catalog }}</td>
                  <td>
                    <span class="badge bg-dark font-monospace">{{ cv.code }}</span>
                  </td>
                  <td>{{ cv.sent_name || '—' }}</td>
                  <td>
                    <span :class="cv.valid ? 'text-dark' : 'text-danger fw-semibold'">
                      {{ cv.official_name }}
                    </span>
                    <div v-if="cv.extra" class="text-muted small">{{ cv.extra }}</div>
                  </td>
                  <td>
                    <span v-if="cv.valid" class="badge bg-success">
                      <i class="fas fa-check me-1"></i> Válido en Catálogo
                    </span>
                    <span v-else class="badge bg-danger">
                      <i class="fas fa-times me-1"></i> No Encontrado
                    </span>
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
          :class="selectedModuleId === mod.id ? 'btn-primary shadow-sm' : 'btn-light border'"
          @click="selectedModuleId = mod.id"
        >
          <i :class="mod.fa_icon" class="me-1"></i>
          {{ mod.title }}
          <span class="badge rounded-pill ms-1" :class="mod.count > 0 ? 'bg-dark' : 'bg-secondary'">
            {{ mod.count }}
          </span>
        </button>
      </div>

      <!-- 3. Desglose de cada Módulo (Nombre Legible y Resultado al Frente) -->
      <div v-for="mod in filteredModules" :key="mod.id" class="glass-card mb-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 border-bottom pb-3 mb-3">
          <div class="d-flex align-items-center gap-2">
            <span class="fs-4" :class="`text-${mod.color}`">
              <i :class="mod.fa_icon"></i>
            </span>
            <h4 class="fw-bold mb-0">{{ mod.title }}</h4>
          </div>
          <span class="badge rounded-pill px-3 py-2" :class="`bg-${mod.color}`">
            {{ mod.count }} registro(s) en este módulo
          </span>
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
          Este Bundle no incluye registros para este módulo.
        </div>
      </div>
    </template>
  </div>
</template>
