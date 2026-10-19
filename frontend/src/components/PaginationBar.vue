<script setup>
defineProps({
  total: {
    type: Number,
    default: 0,
  },
  page: {
    type: Number,
    default: 1,
  },
  numPages: {
    type: Number,
    default: 1,
  },
  hasPrevious: {
    type: Boolean,
    default: false,
  },
  hasNext: {
    type: Boolean,
    default: false,
  },
  previousPage: {
    type: Number,
    default: null,
  },
  nextPage: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['change-page'])
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
    <small class="text-muted fw-bold">
      <i class="fas fa-database me-1"></i>
      Total en base de datos: {{ total }}
    </small>

    <nav aria-label="Page navigation">
      <ul class="pagination pagination-sm mb-0">
        <template v-if="hasPrevious">
          <li class="page-item">
            <button
              type="button"
              class="page-link"
              aria-label="Primero"
              @click="emit('change-page', 1)"
            >
              <span aria-hidden="true">&laquo;&laquo;</span>
            </button>
          </li>
          <li class="page-item">
            <button
              type="button"
              class="page-link"
              aria-label="Anterior"
              @click="emit('change-page', previousPage)"
            >
              <span aria-hidden="true">&laquo;</span>
            </button>
          </li>
        </template>
        <template v-else>
          <li class="page-item disabled"><span class="page-link">&laquo;&laquo;</span></li>
          <li class="page-item disabled"><span class="page-link">&laquo;</span></li>
        </template>

        <li class="page-item disabled">
          <span class="page-link">Página {{ page }} de {{ numPages }}</span>
        </li>

        <template v-if="hasNext">
          <li class="page-item">
            <button
              type="button"
              class="page-link"
              aria-label="Siguiente"
              @click="emit('change-page', nextPage)"
            >
              <span aria-hidden="true">&raquo;</span>
            </button>
          </li>
          <li class="page-item">
            <button
              type="button"
              class="page-link"
              aria-label="Último"
              @click="emit('change-page', numPages)"
            >
              <span aria-hidden="true">&raquo;&raquo;</span>
            </button>
          </li>
        </template>
        <template v-else>
          <li class="page-item disabled"><span class="page-link">&raquo;</span></li>
          <li class="page-item disabled"><span class="page-link">&raquo;&raquo;</span></li>
        </template>
      </ul>
    </nav>
  </div>
</template>
