<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'Buscar...',
  },
  regimenes: {
    type: Array,
    default: () => [],
  },
  selectedRegimen: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'update:selectedRegimen', 'search'])

const localQuery = ref(props.modelValue)
let debounceTimer = null

watch(
  () => props.modelValue,
  (val) => {
    if (val !== localQuery.value) {
      localQuery.value = val
    }
  }
)

function onInput(event) {
  const val = event.target.value
  localQuery.value = val
  emit('update:modelValue', val)

  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('search', { q: val.trim(), regimen: props.selectedRegimen })
  }, 300)
}

function clearSearch() {
  localQuery.value = ''
  emit('update:modelValue', '')
  clearTimeout(debounceTimer)
  emit('search', { q: '', regimen: props.selectedRegimen })
}

function selectRegimen(value) {
  emit('update:selectedRegimen', value)
  emit('search', { q: localQuery.value.trim(), regimen: value })
}
</script>

<template>
  <div class="mb-4">
    <form class="d-flex flex-column flex-md-row gap-3" @submit.prevent>
      <div
        class="input-group input-group-lg flex-grow-1 position-relative shadow-sm rounded-pill bg-white"
        style="border: 1px solid rgba(0,0,0,0.05); transition: all 0.3s ease;"
      >
        <span class="input-group-text bg-transparent border-0 text-primary px-4" style="z-index: 10;">
          <i class="fas fa-search"></i>
        </span>
        <input
          type="text"
          class="form-control border-0 bg-transparent py-3 ps-0"
          :placeholder="placeholder"
          :value="localQuery"
          style="box-shadow: none; font-size: 1.1rem; outline: none;"
          @input="onInput"
        />
        <button
          v-show="localQuery.length > 0"
          type="button"
          class="btn border-0 bg-transparent text-muted px-4"
          style="z-index: 10;"
          title="Limpiar búsqueda"
          @click="clearSearch"
        >
          <i class="fas fa-times-circle fs-5 opacity-75"></i>
        </button>
      </div>

      <div
        v-if="regimenes && regimenes.length > 0"
        class="dropdown shadow-sm rounded-pill bg-white"
        style="border: 1px solid rgba(0,0,0,0.05);"
      >
        <button
          class="btn form-select-lg border-0 bg-transparent rounded-pill py-3 px-4 text-secondary fw-medium dropdown-toggle d-flex justify-content-between align-items-center w-100"
          type="button"
          data-bs-toggle="dropdown"
          aria-expanded="false"
          style="box-shadow: none; min-width: 220px;"
        >
          <span>{{ selectedRegimen || 'Todos los Regímenes' }}</span>
        </button>
        <ul
          class="dropdown-menu border-0 shadow w-100"
          style="border-radius: 15px; max-height: 300px; overflow-y: auto;"
        >
          <li>
            <a
              class="dropdown-item py-2 px-4"
              :class="{ 'active bg-primary text-white': !selectedRegimen }"
              href="#"
              @click.prevent="selectRegimen('')"
            >
              Todos los Regímenes
            </a>
          </li>
          <li v-for="reg in regimenes" :key="reg">
            <a
              class="dropdown-item py-2 px-4"
              :class="{ 'active bg-primary text-white': reg === selectedRegimen }"
              href="#"
              @click.prevent="selectRegimen(reg)"
            >
              {{ reg }}
            </a>
          </li>
        </ul>
      </div>
    </form>
  </div>
</template>
