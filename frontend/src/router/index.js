import { createRouter, createWebHistory } from 'vue-router'
import { authState, verifySession } from '../stores/auth'

import DashboardView from '../views/DashboardView.vue'
import EntidadesView from '../views/EntidadesView.vue'
import Cie10View from '../views/Cie10View.vue'
import CupsView from '../views/CupsView.vue'
import ImportView from '../views/ImportView.vue'
import DocsView from '../views/DocsView.vue'
import LoginView from '../views/LoginView.vue'
import FhirInspectorView from '../views/FhirInspectorView.vue'

const routes = [
  {
    path: '/',
    name: 'dashboard_index',
    component: DashboardView,
    meta: { title: 'API SM Panel' },
  },
  {
    path: '/entidades',
    name: 'manage_entidades',
    component: EntidadesView,
    meta: { title: 'Gestión de Entidades - API SM' },
  },
  {
    path: '/cie10',
    name: 'manage_cie10',
    component: Cie10View,
    meta: { title: 'Gestión de CIE10 - API SM' },
  },
  {
    path: '/cups',
    name: 'manage_cups',
    component: CupsView,
    meta: { title: 'Gestión de CUPS - API SM' },
  },
  {
    path: '/inspector-fhir',
    name: 'fhir_inspector',
    component: FhirInspectorView,
    meta: { title: 'Inspector y Traductor FHIR (Res. 1888) - API SM' },
  },
  {
    path: '/importar',
    name: 'import_data',
    component: ImportView,
    meta: { title: 'Importador Maestro - API SM', requiresAdmin: true },
  },
  {
    path: '/docs',
    name: 'api_docs',
    component: DocsView,
    meta: { title: 'Documentación API - API SM' },
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { title: 'Acceso Administrador - API SM' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  document.title = to.meta.title || 'API SM Panel'

  if (to.meta.requiresAdmin) {
    const ok = await verifySession()
    if (!ok || !authState.user?.is_superuser) {
      return next({ name: 'login', query: { next: to.fullPath } })
    }
  }

  if (to.name === 'login' && authState.isAuthenticated) {
    return next({ name: 'dashboard_index' })
  }

  next()
})

export default router
