<script setup>
import { ref, onMounted } from 'vue'
import { apiService } from '../services/api'

const stats = ref({
  count_entidades: 0,
  count_cie10: 0,
  count_cups: 0,
})
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await apiService.getStats()
    stats.value = data
  } catch (err) {
    console.error('Error cargando estadísticas:', err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <div class="row align-items-stretch">
      <!-- EPS -->
      <div class="col-md-4 mb-4">
        <div class="glass-card text-center h-100 d-flex flex-column">
          <div class="display-4 text-primary mb-3"><i class="fas fa-hospital"></i></div>
          <h3 class="h4 flex-grow-1 d-flex align-items-center justify-content-center mb-3">
            Entidades
          </h3>
          <div>
            <p class="display-6 fw-bold text-dark mb-0">
              {{ loading ? '...' : stats.count_entidades }}
            </p>
            <p class="text-muted mb-3">Registros activos</p>
            <RouterLink :to="{ name: 'manage_entidades' }" class="btn btn-premium w-100 mt-auto">
              Gestionar
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- CIE10 -->
      <div class="col-md-4 mb-4">
        <div class="glass-card text-center h-100 d-flex flex-column">
          <div class="display-4 text-success mb-3"><i class="fas fa-stethoscope"></i></div>
          <h3 class="h4 flex-grow-1 d-flex align-items-center justify-content-center mb-3">
            Diagnósticos (CIE10)
          </h3>
          <div>
            <p class="display-6 fw-bold text-dark mb-0">
              {{ loading ? '...' : stats.count_cie10 }}
            </p>
            <p class="text-muted mb-3">Registros activos</p>
            <RouterLink
              :to="{ name: 'manage_cie10' }"
              class="btn btn-premium w-100 mt-auto"
              style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);"
            >
              Gestionar
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- CUPS -->
      <div class="col-md-4 mb-4">
        <div class="glass-card text-center h-100 d-flex flex-column">
          <div class="display-4 text-warning mb-3"><i class="fas fa-syringe"></i></div>
          <h3 class="h4 flex-grow-1 d-flex align-items-center justify-content-center mb-3">
            Clasificación Única de Procedimientos en Salud (CUPS)
          </h3>
          <div>
            <p class="display-6 fw-bold text-dark mb-0">
              {{ loading ? '...' : stats.count_cups }}
            </p>
            <p class="text-muted mb-3">Registros activos</p>
            <RouterLink
              :to="{ name: 'manage_cups' }"
              class="btn btn-premium w-100 mt-auto"
              style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);"
            >
              Gestionar
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- Disclaimer Legal -->
    <div class="mt-5 text-center">
      <div
        class="p-4 rounded-4"
        style="background-color: rgba(0,0,0,0.02); border: 1px dashed rgba(0,0,0,0.1);"
      >
        <p class="text-muted small mb-0" style="line-height: 1.6;">
          <i class="fas fa-info-circle me-1"></i>
          <strong>Aviso Legal:</strong> Esta es una herramienta de consulta no oficial. Los datos
          presentados se basan en los catálogos del Ministerio de Salud (SISPRO), pero no
          garantizamos su actualización en tiempo real. La responsabilidad de validar los códigos
          para la facturación final recae en el usuario.
        </p>
      </div>
    </div>
  </div>
</template>
