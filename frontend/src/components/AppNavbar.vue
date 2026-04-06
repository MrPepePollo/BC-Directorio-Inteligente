<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import { Sun, Moon, FolderSearch, Search, LogIn, LogOut, User } from 'lucide-vue-next'
import { useDarkMode } from '@/composables/useDarkMode'
import { useAuth } from '@/composables/useAuth'

const { isDark, toggle } = useDarkMode()
const { user, loading, logout } = useAuth()
const route = useRoute()
const router = useRouter()

const navLinks = computed(() =>
  [
    { to: '/', label: 'Directorio', icon: FolderSearch, requiresAuth: false },
    { to: '/search', label: 'Buscar IA', icon: Search, requiresAuth: true },
  ].filter((link) => !link.requiresAuth || !!user.value),
)

async function handleLogout() {
  await logout()
  router.push('/')
}
</script>

<template>
  <header class="sticky top-0 z-50 px-3 pt-3 sm:px-4">
    <div class="app-panel mx-auto flex h-16 max-w-6xl items-center justify-between rounded-[1.35rem] px-3 sm:px-4">
      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-3 text-text-primary">
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-linear-to-br from-primary-500 via-primary-600 to-ai-300 shadow-[0_18px_44px_-24px_rgb(52_116_242_/_0.62)]">
          <span class="text-xs font-extrabold tracking-[0.08em] text-white">NX</span>
        </div>
        <div class="hidden min-w-0 sm:block">
          <span class="block text-sm font-semibold leading-none">Nexo</span>
          <span class="mt-1 block text-[11px] uppercase tracking-[0.16em] text-text-muted">
            Directorio inteligente
          </span>
        </div>
      </RouterLink>

      <!-- Nav Links -->
      <nav class="flex items-center gap-1 rounded-2xl bg-surface-secondary/80 p-1">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          :class="[
            'flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-[background-color,color,transform,box-shadow] duration-200',
            route.path === link.to
              ? 'bg-linear-to-r from-primary-600 to-primary-500 text-white shadow-[0_18px_42px_-26px_rgb(46_108_234_/_0.5)]'
              : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary',
          ]"
        >
          <component :is="link.icon" class="w-4 h-4" />
          <span class="hidden sm:block">{{ link.label }}</span>
        </RouterLink>
      </nav>

      <!-- Actions -->
      <div class="flex items-center gap-2">
        <!-- Authenticated: New + User menu -->
        <template v-if="user">
          <div class="hidden items-center gap-2 rounded-xl border border-border bg-surface-secondary/80 px-3 py-2 text-sm text-text-secondary md:flex">
            <User class="w-4 h-4" />
            <span class="max-w-[140px] truncate">
              {{ user.user_metadata?.full_name || user.email }}
            </span>
          </div>

          <button
            @click="handleLogout"
            class="rounded-xl p-2 text-text-secondary transition-colors duration-200 hover:bg-surface-hover hover:text-danger cursor-pointer"
            title="Cerrar sesion"
          >
            <LogOut class="w-4 h-4" />
          </button>
        </template>

        <!-- Not authenticated: Login -->
        <template v-else-if="!loading">
          <RouterLink
            to="/login"
            class="inline-flex items-center gap-1.5 rounded-xl border border-transparent bg-linear-to-b from-primary-500 to-primary-600 px-3.5 py-2 text-sm font-semibold text-white shadow-[0_24px_60px_-28px_rgb(46_108_234_/_0.42)] transition-[transform,filter] duration-200 hover:-translate-y-0.5"
          >
            <LogIn class="w-4 h-4" />
            <span class="hidden sm:block">Ingresar</span>
          </RouterLink>
        </template>

        <button
          @click="toggle"
          class="rounded-xl border border-border bg-surface-secondary/80 p-2 text-text-secondary transition-[background-color,color,border-color,transform] duration-200 cursor-pointer hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-hover hover:text-text-primary"
          :aria-label="isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
        >
          <Moon v-if="!isDark" class="w-4 h-4" />
          <Sun v-else class="w-4 h-4" />
        </button>
      </div>
    </div>
  </header>
</template>
