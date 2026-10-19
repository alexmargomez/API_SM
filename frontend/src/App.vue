<script setup>
import { onMounted } from 'vue'
import SidebarNav from './components/SidebarNav.vue'
import { authState, clearFlash, verifySession } from './stores/auth'

onMounted(() => {
  verifySession()
})
</script>

<template>
  <div>
    <SidebarNav />

    <main class="main-content">
      <div
        v-if="authState.flashMessage"
        :class="`alert alert-${authState.flashType} alert-dismissible fade show`"
        role="alert"
        style="border-radius: 12px; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05);"
      >
        {{ authState.flashMessage }}
        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="clearFlash"
        ></button>
      </div>

      <RouterView />
    </main>
  </div>
</template>
