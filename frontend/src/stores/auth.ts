import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface AuthUser { id: string; email: string; name: string; autonomy: string }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/auth${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.error?.message === 'string' ? body.error.message : '请求失败，请稍后重试')
  }
  return (await response.json()).data as T
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)

  async function restore() {
    if (initialized.value) return
    try {
      user.value = await request<AuthUser>('/me')
    } catch {
      try { user.value = await request<AuthUser>('/refresh', { method: 'POST' }) }
      catch { user.value = null }
    } finally { initialized.value = true }
  }

  async function login(email: string, password: string) {
    user.value = await request<AuthUser>('/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    initialized.value = true
  }

  async function register(name: string, email: string, password: string) {
    user.value = await request<AuthUser>('/register', { method: 'POST', body: JSON.stringify({ name, email, password }) })
    initialized.value = true
  }

  async function logout() {
    await request<{ ok: boolean }>('/logout', { method: 'POST' })
    user.value = null
  }

  return { user, initialized, restore, login, register, logout }
})
