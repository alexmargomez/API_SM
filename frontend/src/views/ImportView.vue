<script setup>
import { ref } from 'vue'
import { apiService } from '../services/api'

const uploadingType = ref(null)
const consoleLogs = ref([])

const catalogCards = [
  {
    type: 'entidades',
    title: 'Entidades',
    icon: 'fas fa-hospital',
    colorClass: 'text-primary',
    btnClass: 'btn-outline-primary',
    description: 'Subir archivo .xlsx o .csv con el catálogo de entidades de salud.',
  },
  {
    type: 'cie10',
    title: 'CIE10',
    icon: 'fas fa-stethoscope',
    colorClass: 'text-success',
    btnClass: 'btn-outline-success',
    description: 'Subir archivo .xlsx o .csv con diagnósticos del año actual.',
  },
  {
    type: 'cups',
    title: 'CUPS',
    icon: 'fas fa-syringe',
    colorClass: 'text-warning',
    btnClass: 'btn-outline-warning text-dark',
    description: 'Subir archivo .xlsx o .csv con procedimientos médicos.',
  },
  {
    type: 'afp',
    title: 'AFP',
    icon: 'fas fa-building',
    colorClass: 'text-info',
    btnClass: 'btn-outline-info text-dark',
    description: 'Subir archivo .xlsx o .csv con el catálogo de entidades AFP.',
  },
]

async function handleFileSelect(type, event) {
  const file = event.target.files?.[0]
  if (!file) return

  uploadingType.value = type
  const timestamp = new Date().toLocaleTimeString('es-CO')

  try {
    const result = await apiService.uploadCatalog(type, file)
    consoleLogs.value.unshift({
      id: Date.now(),
      status: 'success',
      time: timestamp,
      text: result.message || `¡Se actualizaron ${result.updated_count} registros correctamente!`,
    })
  } catch (err) {
    consoleLogs.value.unshift({
      id: Date.now(),
      status: 'danger',
      time: timestamp,
      text: err.message || 'Error procesando el archivo.',
    })
  } finally {
    uploadingType.value = null
    event.target.value = ''
  }
}
</script>

<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="fas fa-upload text-primary me-2"></i> Importador Maestro</h2>
    </div>

    <div
      class="alert alert-warning d-flex align-items-center shadow-sm mb-4"
      role="alert"
      style="border-radius: 12px; border-left: 5px solid #ffc107;"
    >
      <i class="fas fa-exclamation-triangle fs-4 me-3"></i>
      <div>
        <strong>¡Precaución Administrador!</strong> Cualquier archivo que subas aquí
        <strong>sobrescribirá inmediatamente</strong> los registros en la base de datos de
        producción. Asegúrate de que el formato de los archivos sea correcto.
      </div>
    </div>

    <div class="row g-4">
      <div
        v-for="card in catalogCards"
        :key="card.type"
        class="col-md-6 col-lg-3"
      >
        <div
          class="glass-card h-100 text-center position-relative border-0 shadow-sm"
          style="transition: all 0.3s ease;"
        >
          <div class="p-4">
            <div class="display-4 mb-3" :class="card.colorClass">
              <i :class="card.icon"></i>
            </div>
            <h4 class="fw-bold">{{ card.title }}</h4>
            <p class="text-muted small mb-4">{{ card.description }}</p>

            <label
              class="btn w-100 fw-bold"
              :class="[card.btnClass, { disabled: uploadingType !== null }]"
              style="cursor: pointer; border-radius: 8px;"
            >
              <template v-if="uploadingType === card.type">
                <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                Procesando...
              </template>
              <template v-else>
                <i class="fas fa-cloud-upload-alt me-2"></i>Seleccionar Archivo
              </template>
              <input
                type="file"
                accept=".xlsx,.csv"
                class="d-none"
                :disabled="uploadingType !== null"
                @change="(e) => handleFileSelect(card.type, e)"
              />
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Consola de Resultados -->
    <div class="mt-5">
      <div class="glass-card shadow-sm border-0 p-0">
        <div
          class="p-3 bg-light border-bottom d-flex align-items-center justify-content-between"
          style="border-radius: 15px 15px 0 0;"
        >
          <div class="d-flex align-items-center">
            <i class="fas fa-terminal me-2 text-secondary"></i>
            <h6 class="mb-0 fw-bold text-secondary">Consola de Resultados</h6>
          </div>
          <button
            v-if="consoleLogs.length > 0"
            type="button"
            class="btn btn-sm btn-link text-muted text-decoration-none"
            @click="consoleLogs = []"
          >
            Limpiar consola
          </button>
        </div>

        <div
          class="p-4"
          style="min-height: 150px; max-height: 400px; overflow-y: auto; background-color: #f8f9fa; border-radius: 0 0 15px 15px;"
        >
          <template v-if="consoleLogs.length > 0">
            <div
              v-for="log in consoleLogs"
              :key="log.id"
              :class="`alert alert-${log.status} mb-2 shadow-sm d-flex align-items-center`"
              role="alert"
              style="border-radius: 8px;"
            >
              <i
                v-if="log.status === 'success'"
                class="fas fa-check-circle fs-4 me-3 text-success"
              ></i>
              <i
                v-else
                class="fas fa-exclamation-circle fs-4 me-3 text-danger"
              ></i>
              <div>
                <small class="text-muted d-block">[{{ log.time }}]</small>
                {{ log.text }}
              </div>
            </div>
          </template>
          <div v-else class="text-center text-muted mt-4">
            <i class="fas fa-inbox fs-2 mb-2 opacity-50"></i>
            <p class="mb-0">Esperando ejecución de importación...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
