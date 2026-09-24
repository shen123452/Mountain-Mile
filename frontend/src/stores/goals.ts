import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PaletteName } from '../components/three/palettes'

export interface Goal {
  id: string; name: string; description: string | null; category: string
  palette_variant: PaletteName; seed: string; weekly_target_minutes: number | null
  status: string; sort_order: number; unlocked_count: number; created_at: string
}
export interface GoalDraft { name: string; description?: string; palette_variant: PaletteName; weekly_target_minutes?: number | null }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/goals${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error?.message ?? '目标请求失败，请稍后重试')
  return body.data as T
}

export const useGoalStore = defineStore('goals', () => {
  const goals = ref<Goal[]>([])
  const loading = ref(false)
  async function load() {
    loading.value = true
    try { goals.value = await request<Goal[]>('') }
    finally { loading.value = false }
  }
  async function create(draft: GoalDraft): Promise<Goal> {
    const goal = await request<Goal>('', { method: 'POST', body: JSON.stringify(draft) })
    goals.value.push(goal)
    return goal
  }
  async function update(id: string, changes: Partial<GoalDraft>): Promise<Goal> {
    const goal = await request<Goal>(`/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
    goals.value = goals.value.map(item => item.id === id ? goal : item)
    return goal
  }
  async function archive(id: string) {
    await request<{ ok: boolean }>(`/${id}`, { method: 'DELETE' })
    goals.value = goals.value.filter(item => item.id !== id)
  }
  return { goals, loading, load, create, update, archive }
})
