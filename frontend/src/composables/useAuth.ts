import { ref, readonly } from 'vue'
import { supabase } from '@/lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

const user = ref<User | null>(null)
const session = ref<Session | null>(null)
const loading = ref(true)

// Initialize: listen to auth state changes (runs once on import)
let initialized = false
function initAuth() {
  if (initialized) return
  initialized = true

  supabase.auth.getSession().then(({ data }) => {
    session.value = data.session
    user.value = data.session?.user ?? null
    loading.value = false
  })

  supabase.auth.onAuthStateChange((_event, s) => {
    session.value = s
    user.value = s?.user ?? null
    loading.value = false
  })
}

initAuth()

export function useAuth() {
  async function sendPasswordReset(email: string) {
    const redirectTo = new URL(`${import.meta.env.BASE_URL}login?mode=recovery`, window.location.origin).toString()
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo })
    if (error) throw error
  }

  async function updatePassword(password: string) {
    const { error } = await supabase.auth.updateUser({ password })
    if (error) throw error
  }

  async function login(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }

  async function register(email: string, password: string, fullName: string) {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    })
    if (error) throw error
  }

  async function logout() {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }

  function getAccessToken(): string | null {
    return session.value?.access_token ?? null
  }

  return {
    user: readonly(user),
    session: readonly(session),
    loading: readonly(loading),
    isAuthenticated: () => !!session.value,
    login,
    register,
    sendPasswordReset,
    updatePassword,
    logout,
    getAccessToken,
  }
}
