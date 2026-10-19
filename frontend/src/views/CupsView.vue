<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiService } from '../services/api'
import SearchFilterBar from '../components/SearchFilterBar.vue'
import PaginationBar from '../components/PaginationBar.vue'

const route = useRoute()
const router = useRouter()

const q = ref(route.query.q || '')
const items = ref([])
const loading = ref(false)
const pagination = ref({
  total: 0,
  page: Number(route.query.page) || 1,
  numPages: 1,
  hasPrevious: false,
  hasNext: false,
  previousPage: null,
  nextPage: null,
})

const exportUrl = apiService.getExportUrl('cups')

async function loadData(page = 1) {
  loading.value = true
  try {
    const query = {}
    if (q.value.trim()) query.q = q.value.trim()
    if (page > 1) query.page = String(page)
    router.replace({ query })

    const data = await apiService.getCups({
      q: q.value.trim(),
      page,
    })

    items.value = data.results || []
    pagination.value = {
      total: data.total || 0,
      page: data.page || 1,
      numPages: data.num_pages || 1,
      hasPrevious: Boolean(data.has_previous),
      hasNext: Boolean(data.has_next),
      previousPage: data.previous_page,
      nextPage: data.next_page,
    }
  } catch (err) {
    console.error('Error cargando CUPS:', err)
  } finally {
    loading.value = false
  }
}

function handleSearch({ q: searchQ }) {
  q.value = searchQ
  loadData(1)
}

function handlePageChange(newPage) {
  loadData(newPage)
}

onMounted(() => {
  loadData(pagination.value.page)
})
</script>

<template>
  <div>
    <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
      <h2 class="mb-0 fs-3">
        <i class="fas fa-syringe text-warning me-2"></i> Gestión de CUPS
      </h2>
      <div class="d-flex gap-2 d-none d-md-flex">
        <a :href="exportUrl" class="btn btn-export w-100 w-md-auto">
          <i class="fas fa-file-csv me-2"></i>Exportar CSV
        </a>
      </div>
    </div>

    <SearchFilterBar
      v-model="q"
      placeholder="Buscar por código o descripción..."
      @search="handleSearch"
    />

    <div class="glass-card">
      <div :style="{ opacity: loading ? '0.5' : '1', transition: 'opacity 0.2s ease' }">
        <div class="table-responsive border-0">
          <table class="table table-hover mb-0">
            <thead>
              <tr>
                <th class="text-nowrap">Código</th>
                <th class="text-nowrap">Descripción</th>
                <th class="text-nowrap">Versión</th>
                <th class="text-nowrap">Fecha Versión</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cup in items" :key="cup.codigo">
                <td><span class="badge bg-warning text-dark">{{ cup.codigo }}</span></td>
                <td>{{ cup.descripcion }}</td>
                <td>{{ cup.version }}</td>
                <td><span class="badge bg-light text-dark">{{ cup.version_fecha || '-' }}</span></td>
              </tr>
              <tr v-if="!loading && items.length === 0">
                <td colspan="4" class="text-center py-4 text-muted">
                  No hay registros disponibles
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <PaginationBar
          :total="pagination.total"
          :page="pagination.page"
          :num-pages="pagination.numPages"
          :has-previous="pagination.hasPrevious"
          :has-next="pagination.hasNext"
          :previous-page="pagination.previousPage"
          :next-page="pagination.nextPage"
          @change-page="handlePageChange"
        />
      </div>
    </div>

    <div class="d-block d-md-none mt-4 mb-3">
      <a :href="exportUrl" class="btn btn-export w-100 py-3 shadow-sm" style="font-size: 1.1rem;">
        <i class="fas fa-file-csv me-2"></i>Exportar CSV
      </a>
    </div>
  </div>
</template>
