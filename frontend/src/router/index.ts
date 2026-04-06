import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import { supabase } from '@/lib/supabase'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { hideNavbar: true },
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/providers/new',
      name: 'provider-create',
      component: () => import('@/views/ProviderFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/providers/:id',
      name: 'provider-detail',
      component: () => import('@/views/ProviderDetailView.vue'),
    },
    {
      path: '/providers/:id/edit',
      name: 'provider-edit',
      component: () => import('@/views/ProviderFormView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const { data } = await supabase.auth.getSession()
    if (!data.session) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
  // Redirect away from login if already authenticated
  if (to.name === 'login') {
    const isRecoveryFlow = to.query.mode === 'recovery' || to.hash.includes('type=recovery')
    const { data } = await supabase.auth.getSession()
    if (data.session && !isRecoveryFlow) {
      return { name: 'home' }
    }
  }
})

export default router
