import { onMounted, onUnmounted, ref } from 'vue'

const STORAGE_KEY = 'theme'
const MEDIA_QUERY = '(prefers-color-scheme: dark)'

function getSystemPreference() {
  return typeof window !== 'undefined' && window.matchMedia(MEDIA_QUERY).matches
}

function getStoredTheme() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(STORAGE_KEY)
}

const isDark = ref(
  typeof document !== 'undefined' ? document.documentElement.classList.contains('dark') : false,
)

function syncTheme(nextValue: boolean) {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  root.classList.add('theme-switching')
  root.classList.toggle('dark', nextValue)
  root.style.colorScheme = nextValue ? 'dark' : 'light'

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      root.classList.remove('theme-switching')
    })
  })
}

export function useDarkMode() {
  let mediaQuery: MediaQueryList | null = null
  let handleSystemChange: ((event: MediaQueryListEvent) => void) | null = null

  onMounted(() => {
    const storedTheme = getStoredTheme()
    const nextValue = storedTheme ? storedTheme === 'dark' : getSystemPreference()
    isDark.value = nextValue
    syncTheme(nextValue)

    mediaQuery = window.matchMedia(MEDIA_QUERY)
    handleSystemChange = (event) => {
      if (getStoredTheme()) return
      isDark.value = event.matches
      syncTheme(event.matches)
    }

    mediaQuery.addEventListener('change', handleSystemChange)
  })

  onUnmounted(() => {
    if (mediaQuery && handleSystemChange) {
      mediaQuery.removeEventListener('change', handleSystemChange)
    }
  })

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    syncTheme(isDark.value)
  }

  return { isDark, toggle }
}
