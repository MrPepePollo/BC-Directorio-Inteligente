<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, KeyRound, MailCheck, ShieldCheck } from 'lucide-vue-next'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/composables/useAuth'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'

type AuthMode = 'login' | 'register' | 'forgot' | 'reset'

const router = useRouter()
const route = useRoute()
const { login, register, sendPasswordReset, updatePassword } = useAuth()

const mode = ref<AuthMode>('login')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const fullName = ref('')
const error = ref('')
const success = ref('')
const submitting = ref(false)

const title = computed(() => {
  if (mode.value === 'register') return 'Crear cuenta'
  if (mode.value === 'forgot') return 'Restablecer contrasena'
  if (mode.value === 'reset') return 'Nueva contrasena'
  return 'Iniciar sesion'
})

const helperText = computed(() => {
  if (mode.value === 'register') {
    return 'Crea tu acceso para administrar proveedores y desbloquear la busqueda inteligente.'
  }
  if (mode.value === 'forgot') {
    return 'Te enviaremos un enlace seguro para que recuperes el acceso a tu cuenta.'
  }
  if (mode.value === 'reset') {
    return 'Define una nueva contrasena para completar la recuperacion de tu cuenta.'
  }
  return 'Ingresa para administrar proveedores y acceder a la busqueda inteligente.'
})

const primaryAction = computed(() => {
  if (mode.value === 'register') return 'Crear cuenta'
  if (mode.value === 'forgot') return 'Enviar enlace'
  if (mode.value === 'reset') return 'Actualizar contrasena'
  return 'Iniciar sesion'
})

const showEmailField = computed(() => mode.value !== 'reset')
const showNameField = computed(() => mode.value === 'register')
const showPasswordField = computed(() => mode.value === 'login' || mode.value === 'register' || mode.value === 'reset')
const showConfirmPasswordField = computed(() => mode.value === 'reset')

function setMode(nextMode: AuthMode) {
  mode.value = nextMode
  error.value = ''
  success.value = ''
  password.value = ''
  confirmPassword.value = ''
}

function syncModeFromRoute() {
  const isRecoveryLink = route.query.mode === 'recovery' || route.hash.includes('type=recovery')
  if (isRecoveryLink) {
    setMode('reset')
    return
  }
  if (mode.value === 'reset') {
    setMode('login')
  }
}

onMounted(() => {
  syncModeFromRoute()

  supabase.auth.onAuthStateChange((event) => {
    if (event === 'PASSWORD_RECOVERY') {
      setMode('reset')
      success.value = ''
    }
  })
})

async function onSubmit() {
  error.value = ''
  success.value = ''
  submitting.value = true

  try {
    if (mode.value === 'register') {
      await register(email.value, password.value, fullName.value)
      const redirect =
        typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
          ? route.query.redirect
          : '/'
      router.push(redirect)
      return
    }

    if (mode.value === 'forgot') {
      await sendPasswordReset(email.value)
      success.value = 'Revisa tu correo. Te enviamos un enlace para restablecer la contrasena.'
      return
    }

    if (mode.value === 'reset') {
      if (password.value.length < 6) {
        throw new Error('La contrasena debe tener al menos 6 caracteres.')
      }
      if (password.value !== confirmPassword.value) {
        throw new Error('Las contrasenas no coinciden.')
      }
      await updatePassword(password.value)
      success.value = 'Tu contrasena fue actualizada correctamente.'
      router.push('/')
      return
    }

    await login(email.value, password.value)
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    router.push(redirect)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error de autenticacion'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="relative overflow-hidden">
    <div class="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgb(58_121_255_/_0.18),_transparent_48%)] blur-3xl" />

    <div class="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl items-center justify-center">
      <div class="w-full max-w-xl">
        <div class="mx-auto max-w-md text-center">
          <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-linear-to-br from-primary-500 via-primary-600 to-ai-300 shadow-[0_24px_60px_-30px_rgb(52_116_242_/_0.55)]">
            <span class="text-xl font-extrabold tracking-[0.08em] text-white">BD</span>
          </div>

          <div class="mt-6 space-y-3">
            <span class="inline-flex rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary-700 dark:border-primary-800 dark:bg-primary-900 dark:text-primary-300">
              Acceso privado
            </span>
            <h1 class="text-4xl font-bold leading-tight text-text-primary sm:text-5xl">
              {{ title }}
            </h1>
            <p class="text-base leading-7 text-text-secondary">
              {{ helperText }}
            </p>
          </div>
        </div>

        <div class="app-panel mx-auto mt-10 max-w-md rounded-[1.9rem] p-3 sm:p-4">
          <div class="rounded-[1.55rem] border border-border/80 bg-surface/70 p-6 sm:p-7">
            <div class="mb-6 flex items-start gap-3">
              <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                <MailCheck v-if="mode === 'forgot'" class="h-5 w-5" />
                <KeyRound v-else-if="mode === 'reset'" class="h-5 w-5" />
                <ShieldCheck v-else class="h-5 w-5" />
              </div>
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Directorio de proveedores inteligente
                </p>
                <h2 class="text-2xl font-semibold text-text-primary">{{ title }}</h2>
              </div>
            </div>

            <form @submit.prevent="onSubmit" class="space-y-4">
              <div
                v-if="error"
                class="rounded-2xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
              >
                {{ error }}
              </div>

              <div
                v-if="success"
                class="rounded-2xl border border-emerald-200 bg-emerald-50/90 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
              >
                {{ success }}
              </div>

              <AppInput
                v-if="showNameField"
                v-model="fullName"
                label="Nombre completo"
                placeholder="Tu nombre"
                required
              />

              <AppInput
                v-if="showEmailField"
                v-model="email"
                label="Email"
                type="email"
                placeholder="tu@email.com"
                required
              />

              <AppInput
                v-if="showPasswordField"
                v-model="password"
                label="Contrasena"
                type="password"
                :placeholder="mode === 'reset' ? 'Nueva contrasena' : 'Minimo 6 caracteres'"
                required
              />

              <AppInput
                v-if="showConfirmPasswordField"
                v-model="confirmPassword"
                label="Confirmar contrasena"
                type="password"
                placeholder="Repite la nueva contrasena"
                required
              />

              <AppButton type="submit" size="lg" class="mt-2 w-full" :loading="submitting">
                {{ primaryAction }}
              </AppButton>
            </form>

            <div class="mt-5 flex flex-col items-center gap-3 text-sm">
              <button
                v-if="mode === 'login'"
                type="button"
                @click="setMode('forgot')"
                class="cursor-pointer font-medium text-primary-600 transition-colors hover:text-primary-500"
              >
                Olvide mi contrasena
              </button>

              <button
                v-if="mode === 'login'"
                type="button"
                @click="setMode('register')"
                class="cursor-pointer font-medium text-primary-600 transition-colors hover:text-primary-500"
              >
                No tienes cuenta? Registrate
              </button>

              <button
                v-if="mode === 'register'"
                type="button"
                @click="setMode('login')"
                class="cursor-pointer font-medium text-primary-600 transition-colors hover:text-primary-500"
              >
                Ya tienes cuenta? Inicia sesion
              </button>

              <button
                v-if="mode === 'forgot' || mode === 'reset'"
                type="button"
                @click="setMode('login')"
                class="inline-flex cursor-pointer items-center gap-2 font-medium text-primary-600 transition-colors hover:text-primary-500"
              >
                <ArrowLeft class="h-4 w-4" />
                Volver a iniciar sesion
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
