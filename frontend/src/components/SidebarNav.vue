<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, logoutAdmin } from '../stores/auth'

const isMobileMenuOpen = ref(false)
const route = useRoute()
const router = useRouter()

function toggleSidebar() {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

function closeSidebar() {
  isMobileMenuOpen.value = false
}

watch(
  () => route.fullPath,
  () => {
    closeSidebar()
  }
)

async function handleLogout() {
  await logoutAdmin()
  router.push({ name: 'dashboard_index' })
}
</script>

<template>
  <div
    class="sidebar-overlay"
    :class="{ show: isMobileMenuOpen }"
    @click="closeSidebar"
  ></div>

  <div class="mobile-header d-md-none">
    <RouterLink
      :to="{ name: 'dashboard_index' }"
      class="sidebar-brand mb-0 text-primary fw-bold fs-4 d-flex align-items-center"
      style="margin-bottom: 0 !important; letter-spacing: -0.5px; text-decoration: none;"
    >
      <i class="fas fa-heartbeat me-2"></i> API SM
    </RouterLink>
    <button class="btn btn-light shadow-sm" @click="toggleSidebar" aria-label="Abrir menú">
      <i class="fas fa-bars"></i>
    </button>
  </div>

  <aside class="sidebar" :class="{ show: isMobileMenuOpen }">
    <RouterLink
      :to="{ name: 'dashboard_index' }"
      class="sidebar-brand d-none d-md-block text-primary"
    >
      <i class="fas fa-heartbeat"></i> API SM
    </RouterLink>

    <nav class="nav flex-column">
      <RouterLink class="nav-link" :to="{ name: 'dashboard_index' }">
        <i class="fas fa-home"></i> Inicio
      </RouterLink>
      <RouterLink class="nav-link" :to="{ name: 'manage_entidades' }">
        <i class="fas fa-hospital"></i> Entidades
      </RouterLink>
      <RouterLink class="nav-link" :to="{ name: 'manage_cie10' }">
        <i class="fas fa-stethoscope"></i> Diagnósticos (CIE10)
      </RouterLink>
      <RouterLink class="nav-link" :to="{ name: 'manage_cups' }">
        <i class="fas fa-syringe"></i> Clasificación Única de Procedimientos en Salud (CUPS)
      </RouterLink>

      <!-- Separador visual para el módulo independiente de Herramientas -->
      <hr class="my-3 mx-3 border-secondary opacity-25" />
      <h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mb-1 text-muted text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.06em;">
        <span>Herramientas Res. 1888</span>
      </h6>
      <RouterLink class="nav-link fw-semibold" :to="{ name: 'fhir_inspector' }">
        <i class="fas fa-microscope text-primary"></i> Inspector FHIR (RDA)
      </RouterLink>

      <template v-if="authState.isAuthenticated && authState.user?.is_superuser">
        <hr class="my-3 mx-3 border-secondary opacity-25" />
        <h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mb-1 text-muted text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.06em;">
          <span>Administración</span>
        </h6>
        <RouterLink class="nav-link fw-bold" :to="{ name: 'import_data' }">
          <i class="fas fa-upload"></i> Importador Maestro
        </RouterLink>
      </template>

      <hr class="my-3 mx-3 border-secondary opacity-25" />
      <h6 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mb-1 text-muted text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.06em;">
        <span>Desarrolladores</span>
      </h6>
      <RouterLink class="nav-link fw-bold" :to="{ name: 'api_docs' }">
        <i class="fa-solid fa-book-open"></i> Documentación API
      </RouterLink>
    </nav>

    <div class="mt-auto p-3 mb-3">
      <button
        v-if="authState.isAuthenticated"
        type="button"
        class="btn btn-light w-100 text-danger fw-bold d-flex justify-content-center align-items-center gap-2"
        style="border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);"
        @click="handleLogout"
      >
        <i class="fas fa-sign-out-alt"></i> Cerrar Sesión
      </button>
      <RouterLink
        v-else
        :to="{ name: 'login' }"
        class="btn btn-primary w-100 fw-bold d-flex justify-content-center align-items-center gap-2"
        style="border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
      >
        <i class="fas fa-lock"></i> Acceso Admin
      </RouterLink>
    </div>
  </aside>
</template>
