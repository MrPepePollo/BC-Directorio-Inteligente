<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { RouterView } from 'vue-router'
import AppNavbar from '@/components/AppNavbar.vue'

const route = useRoute()
const showNavbar = computed(() => !route.meta.hideNavbar)
const mainClassName = computed(() =>
  route.meta.hideNavbar
    ? 'min-h-screen px-4 py-8 sm:px-6'
    : 'mx-auto max-w-6xl px-4 pb-10 pt-8',
)
</script>

<template>
  <div class="min-h-screen">
    <AppNavbar v-if="showNavbar" />
    <main :class="mainClassName">
      <RouterView v-slot="{ Component }">
        <KeepAlive include="SearchView">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
  </div>
</template>
