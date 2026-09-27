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
  let keepAliveTimer: number | undefined
  let visibilityBound = false
  // 进行中的 restore() 共享 promise:App 的 onMounted 与路由守卫可能同时调用,
  // 若各自起一份会话恢复,守卫会在恢复完成前检查 user,误把已登录用户踢回 /login。
  let restoring: Promise<void> | null = null

  // 会话保活:access token 15 分钟过期,每 10 分钟静默续期;
  // 切回标签页时立即续期(后台标签页定时器可能被浏览器节流)。
  async function ensureSession() {
    try {
      user.value = await request<AuthUser>('/me')
      return true
    } catch {
      try { user.value = await request<AuthUser>('/refresh', { method: 'POST' }); return true }
      catch { user.value = null; return false }
    }
  }

  function startSessionKeeper() {
    if (keepAliveTimer) return
    keepAliveTimer = window.setInterval(() => { if (user.value) void ensureSession() }, 10 * 60 * 1000)
    if (!visibilityBound) {
      visibilityBound = true
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && user.value) void ensureSession()
      })
    }
  }

  async function restore() {
    if (restoring) return restoring
    if (initialized.value) return
    initialized.value = true
    restoring = (async () => {
      try {
        const ok = await ensureSession()
        if (ok) startSessionKeeper()
      } finally {
        restoring = null
      }
    })()
    return restoring
  }

  async function login(email: string, password: string) {
    user.value = await request<AuthUser>('/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    initialized.value = true
    startSessionKeeper()
  }

  async function register(name: string, email: string, password: string) {
    user.value = await request<AuthUser>('/register', { method: 'POST', body: JSON.stringify({ name, email, password }) })
    initialized.value = true
    startSessionKeeper()
  }

  async function logout() {
    await request<{ ok: boolean }>('/logout', { method: 'POST' })
    user.value = null
    if (keepAliveTimer) { window.clearInterval(keepAliveTimer); keepAliveTimer = undefined }
  }

  async function setAutonomy(autonomy: string) {
    user.value = await request<AuthUser>('/autonomy', { method: 'PATCH', body: JSON.stringify({ autonomy }) })
  }

  return { user, initialized, restore, login, register, logout, setAutonomy }
})
