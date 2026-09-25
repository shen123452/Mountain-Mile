<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

type Status = 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'rejected'
interface Run { id: string; goal: string; status: Status; current_step: number; role: string; summary: string | null; error: string | null; prompt_tokens: number; completion_tokens: number; estimated_cost: number }
interface Step { number: number; title: string; detail: string | null; role: string; status: string }
interface Approval { id: string; status: string; payload: Record<string, unknown> }
interface Detail extends Run { steps: Step[]; approvals: Approval[] }

const runs = ref<Run[]>([])
const selected = ref<Detail | null>(null)
function renderMd(text: string) {
  return DOMPurify.sanitize(marked.parse(text, { async: false, breaks: true }) as string)
}
const replyHtml = computed(() => selected.value?.summary ? renderMd(selected.value.summary) : '')
const orderedRuns = computed(() => [...runs.value].reverse())
const currentTitle = computed(() => selected.value?.goal ?? runs.value[0]?.goal ?? '新的运行')
const fileInput = ref<HTMLInputElement | null>(null)
const uploadNote = ref('')

function toggleSteps(run: Run) {
  if (selected.value?.id === run.id) { stepsOpen.value = !stepsOpen.value; return }
  void open(run.id)
}

async function uploadFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]; if (!file) return
  const form = new FormData(); form.append('file', file)
  try {
    const response = await fetch('/api/knowledge/documents', { method: 'POST', credentials: 'include', body: form })
    const body = await response.json(); if (!response.ok) throw new Error(body.error?.message ?? body.detail ?? '上传失败')
    uploadNote.value = `已上传「${file.name}」到资料库，学习对话将能引用它`
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '上传失败' } finally { input.value = '' }
}
const goal = ref('')
const payload = ref('')
const busy = ref(false)
const error = ref('')
const liveEvents = ref<{ id: number; type: string; text: string }[]>([])
let stream: EventSource | null = null
const mobilePanel = ref<'history' | 'chat'>('chat')
const autonomyMenuOpen = ref(false)
const runsOpen = ref(true)
const tasksOpen = ref(true)
const expandedSteps = ref<Set<number>>(new Set())
const stepsOpen = ref(false)
const stepSummary = computed(() => {
  const steps = selected.value?.steps ?? []
  const tools = steps.filter(item => item.kind === 'tool').length
  return steps.length ? `${steps.length} 步 · ${tools} 次工具调用` : ''
})
const failedCount = computed(() => (selected.value?.steps ?? []).filter(item => item.status === 'failed').length)

interface TaskItem { key: string; kind: 'todo' | 'plan'; id: string; title: string; dueLabel: string; overdue: boolean }
const tasks = ref<TaskItem[]>([])
const taskCount = computed(() => tasks.value.length)

function dueInfo(due: string | null): { label: string; overdue: boolean } {
  if (!due) return { label: '', overdue: false }
  const date = new Date(`${due}T00:00:00`)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const diff = Math.round((date.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return { label: '今天到期', overdue: false }
  if (diff < 0) return { label: `逾期 ${-diff} 天`, overdue: true }
  return { label: `${date.getMonth() + 1}/${date.getDate()} 到期`, overdue: false }
}

async function loadTasks() {
  try {
    const body = await fetch('/api/tasks', { credentials: 'include' }).then(r => r.json())
    const items: TaskItem[] = []
    for (const item of body.data?.todos ?? []) {
      const info = dueInfo(item.due_date)
      items.push({ key: `t-${item.id}`, kind: 'todo', id: item.id, title: item.title, dueLabel: info.label, overdue: info.overdue })
    }
    for (const item of body.data?.plan_tasks ?? []) {
      const info = dueInfo(item.due_date)
      items.push({ key: `p-${item.id}`, kind: 'plan', id: item.id, title: item.title, dueLabel: info.label, overdue: info.overdue })
    }
    tasks.value = items
  } catch { /* 静默 */ }
}

async function toggleTask(task: TaskItem) {
  const path = task.kind === 'todo' ? `/api/tasks/todos/${task.id}/toggle` : `/api/tasks/plan-tasks/${task.id}/toggle`
  try { await fetch(path, { method: 'POST', credentials: 'include' }); tasks.value = tasks.value.filter(item => item.key !== task.key) } catch { /* 静默 */ }
}

async function archiveTask(task: TaskItem) {
  const path = task.kind === 'todo' ? `/api/tasks/todos/${task.id}/archive` : `/api/tasks/plan-tasks/${task.id}/archive`
  try { await fetch(path, { method: 'POST', credentials: 'include' }); tasks.value = tasks.value.filter(item => item.key !== task.key) } catch { /* 静默 */ }
}

async function deleteTask(task: TaskItem) {
  if (!window.confirm('删除该任务？此操作不可恢复。')) return
  const path = task.kind === 'todo' ? `/api/tasks/todos/${task.id}` : `/api/tasks/plan-tasks/${task.id}`
  try { await fetch(path, { method: 'DELETE', credentials: 'include' }); tasks.value = tasks.value.filter(item => item.key !== task.key) } catch { /* 静默 */ }
}
const mainRef = ref<HTMLElement | null>(null)

function toggleStep(number: number) {
  const next = new Set(expandedSteps.value)
  if (next.has(number)) next.delete(number); else next.add(number)
  expandedSteps.value = next
}
function scrollMainToBottom() {
  void nextTick(() => mainRef.value?.scrollTo({ top: mainRef.value.scrollHeight, behavior: 'smooth' }))
}
const auth = useAuthStore()
const autonomyOptions = [
  { id: 'L0', title: '步步确认', detail: '所有写入都先询问', pill: '每次写入前询问' },
  { id: 'L1', title: '低风险自动', detail: '待办与复习自动执行', pill: '低风险自动执行' },
  { id: 'L2', title: '高自主', detail: '高风险动作仍需确认', pill: '允许完全访问' },
]
const currentAutonomy = computed(() => autonomyOptions.find(option => option.id === auth.user?.autonomy) ?? autonomyOptions[0])
function pickAutonomy(id: string) {
  void setAutonomy(id)
  autonomyMenuOpen.value = false
}
const roleLabels: Record<string, string> = { Planner: '规划者', Executor: '执行者', Reflector: '复盘者', Curator: '记忆官', Scout: '向导' }
const kindLabels: Record<string, string> = { tool: '工具', message: '回复', handoff: '委派' }
function statusText(status: string) { return (labels as Record<string, string>)[status] ?? status }

async function setAutonomy(level: string) {
  try { await auth.setAutonomy(level) } catch (cause) { error.value = cause instanceof Error ? cause.message : '自主档位更新失败' }
}


const labels: Record<Status, string> = {
  queued: '排队中', running: '执行中', awaiting_approval: '等待审批',
  completed: '已完成', failed: '失败', rejected: '已拒绝',
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/agent/runs${path}`, {
    credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail ?? body.error?.message ?? '请求失败，请稍后重试')
  return body.data as T
}

async function refresh(id?: string) {
  runs.value = await request<Run[]>('')
  const target = id ?? selected.value?.id ?? runs.value[0]?.id
  if (target) await open(target)
}

async function open(id: string) {
  expandedSteps.value = new Set()
  const previous = selected.value?.status
  selected.value = await request<Detail>(`/${id}`)
  // 运行中自动展开执行过程;从运行态转入终态时自动收起,其余保持用户选择
  const active = ['queued', 'running', 'awaiting_approval'].includes(selected.value.status)
  if (active) stepsOpen.value = true
  else if (previous && ['queued', 'running', 'awaiting_approval'].includes(previous)) stepsOpen.value = false
  const pending = selected.value.approvals.find(item => item.status === 'pending')
  // 用户已在编辑参数时不覆盖;无待审批时清空
  if (pending && !payload.value) payload.value = JSON.stringify(pending.payload, null, 2)
  if (!pending) payload.value = ''
}

async function start() {
  if (!goal.value.trim() || busy.value) return
  busy.value = true; error.value = ''
  try {
    const run = await request<Run>('', { method: 'POST', body: JSON.stringify({ goal: goal.value.trim() }) })
    goal.value = ''
    await refresh(run.id)
    watchRun(run.id)
    stepsOpen.value = true
    scrollMainToBottom()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法启动运行' }
  finally { busy.value = false }
}

function watchRun(id: string) {
  stream?.close(); liveEvents.value = []
  stream = new EventSource(`/api/agent/runs/${id}/stream`, { withCredentials: true })
  const handle = (event: MessageEvent) => {
    const payload = JSON.parse(event.data) as Record<string, unknown>
    liveEvents.value.push({ id: Number(event.lastEventId || Date.now()), type: event.type, text: String(payload.title ?? payload.status ?? payload.summary ?? payload.tool ?? '运行事件') })
    if (['step', 'phase', 'status'].includes(event.type)) scrollMainToBottom()
    if (event.type === 'done' || event.type === 'approval') void refresh(id)
  }
  for (const type of ['status', 'phase', 'step', 'approval', 'done']) stream.addEventListener(type, handle)
  stream.onerror = () => { if (['completed', 'failed', 'cancelled'].includes(selected.value?.status ?? '')) stream?.close() }
}

async function deleteRun(run: Run) {
  if (!window.confirm('删除该运行及其全部轨迹记录？此操作不可恢复。')) return
  try {
    await request(`/${run.id}`, { method: 'DELETE' })
    runs.value = runs.value.filter(item => item.id !== run.id)
    if (selected.value?.id === run.id) { stream?.close(); stream = null; selected.value = null }
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '删除失败' }
}

async function archiveRun(run: Run) {
  try {
    await request(`/${run.id}/archive`, { method: 'POST' })
    runs.value = runs.value.filter(item => item.id !== run.id)
    if (selected.value?.id === run.id) { stream?.close(); stream = null; selected.value = null }
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '归档失败' }
}

async function cancel() {
  if (!selected.value || busy.value) return
  busy.value = true
  try { await request<Run>(`/${selected.value.id}/cancel`, { method: 'POST' }); await refresh(selected.value.id) } catch (cause) { error.value = cause instanceof Error ? cause.message : '中断失败' } finally { busy.value = false }
}

async function decide(decision: 'approve' | 'reject') {
  if (!selected.value || busy.value) return
  let edited_payload: Record<string, unknown> | undefined
  if (decision === 'approve') {
    try {
      const parsed: unknown = JSON.parse(payload.value)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('参数须为 JSON 对象')
      edited_payload = parsed as Record<string, unknown>
    } catch { error.value = '参数格式错误，请填写 JSON 对象'; return }
  }
  busy.value = true; error.value = ''
  try {
    const run = await request<Run>(`/${selected.value.id}/approval`, {
      method: 'POST', body: JSON.stringify({ decision, edited_payload }),
    })
    await refresh(run.id)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '审批失败' }
  finally { busy.value = false }
}

let pollTimer: number | undefined
async function poll() {
  // 兜底轮询:SSE 断线、页面刷新后的挂起运行、审批状态变化都能被看到
  try {
    runs.value = await request<Run[]>('')
    const watching = runs.value.find(item => item.id === selected.value?.id)
    if (watching && ['queued', 'running', 'awaiting_approval'].includes(watching.status)) await open(watching.id)
    void loadTasks()
  } catch { /* 轮询失败静默,下个周期重试 */ }
}

onMounted(() => {
  void Promise.all([refresh(), loadTasks()]).catch(cause => { error.value = cause instanceof Error ? cause.message : '加载失败' })
  pollTimer = window.setInterval(() => void poll(), 6000)
})
onUnmounted(() => { stream?.close(); if (pollTimer) window.clearInterval(pollTimer) })
</script>

<template>
  <div class="agent-workspace" :class="`panel-${mobilePanel}`">
    <aside class="run-rail" aria-label="运行记录">
      <div class="rail-brand"><span class="brand-mark">MM</span><div><strong>山程向导</strong><small>学习节奏工作台</small></div></div>
      <button type="button" class="new-run" @click="goal = ''; mobilePanel = 'chat'">新建运行</button>
      <button type="button" class="rail-group" @click="tasksOpen = !tasksOpen"><span class="group-chev">{{ tasksOpen ? '▾' : '▸' }}</span>我的任务<span>{{ taskCount }}</span></button>
      <div v-show="tasksOpen" class="task-list">
        <p v-if="!taskCount" class="muted">暂无待办 · 向导可以帮你创建</p>
        <div v-for="task in tasks" :key="task.key" class="task-item">
          <i class="task-check" role="button" aria-label="标记完成" title="标记完成" @click="toggleTask(task)"></i><span class="task-title">{{ task.title }}</span><small v-if="task.dueLabel" :class="{ overdue: task.overdue }">{{ task.dueLabel }}</small><span class="task-ops"><button type="button" class="task-op" title="归档:从列表隐藏但保留记录" @click="archiveTask(task)">归档</button><button type="button" class="task-op danger" title="删除:不可恢复" @click="deleteTask(task)">删除</button></span>
        </div>
      </div>
      <button type="button" class="rail-group" @click="runsOpen = !runsOpen"><span class="group-chev">{{ runsOpen ? '▾' : '▸' }}</span>最近运行<span>{{ runs.length }}</span></button>
      <div v-show="runsOpen">
        <p v-if="!runs.length" class="muted">还没有运行记录</p>
        <div v-for="run in runs" :key="run.id" class="run-item" :class="{ active: selected?.id === run.id }" :data-status="run.status">
          <div class="run-main" role="button" @click="open(run.id)"><span class="run-goal-text">{{ run.goal }}</span><small>{{ labels[run.status] }}</small></div>
          <span class="run-ops">
            <button type="button" class="icon-op" title="归档:从列表隐藏但保留记录" @click="archiveRun(run)"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4"/></svg></button>
            <button type="button" class="icon-op danger" title="删除:含全部轨迹,不可恢复" @click="deleteRun(run)"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14z"/></svg></button>
          </span>
        </div>
      </div>
    </aside>
    <section ref="mainRef" class="agent-main">
      <header class="agent-topbar"><strong>{{ currentTitle }}</strong><span v-if="selected" class="badge" :data-status="selected.status">{{ labels[selected.status] }}</span><span class="connection"><i></i> 本地工作区</span></header>
      <p v-if="error" class="agent-error" role="alert">{{ error }}</p>
      <p v-if="uploadNote" class="upload-note">{{ uploadNote }}</p>
      <div class="run-flow">
        <p v-if="!runs.length" class="flow-empty">还没有运行记录——在下方输入，让向导替你做第一件事。</p>
        <template v-for="run in orderedRuns" :key="run.id">
          <div class="flow-row user"><span class="flow-avatar">你</span><div class="flow-bubble user-bubble">{{ run.goal }}</div></div>
          <div class="flow-row assistant">
            <span class="flow-avatar mm">MM</span>
            <div class="flow-bubble wizard-bubble">
              <div class="wizard-head">
                <span class="badge" :data-status="run.status">{{ labels[run.status] }}</span>
                <span v-if="run.prompt_tokens" class="flow-meta">{{ run.current_step }} 步 · ¥{{ run.estimated_cost.toFixed(4) }}</span>
                <button v-if="['queued','running'].includes(run.status) && selected?.id === run.id" type="button" class="cancel-button" :disabled="busy" @click="cancel">中断</button>
              </div>
              <ol v-if="selected?.id === run.id && liveEvents.length && ['running','queued'].includes(run.status)" class="event-stream" aria-live="polite"><li v-for="item in liveEvents" :key="item.id" :data-type="item.type"><i class="event-dot"></i><span>{{ item.text }}</span></li></ol>
              <button type="button" class="steps-toggle" @click="toggleSteps(run)"><span class="chev">{{ selected?.id === run.id && stepsOpen ? '▾' : '▸' }}</span><strong>执行过程</strong><span v-if="selected?.id === run.id" class="steps-meta">{{ stepSummary }}</span><span v-if="selected?.id === run.id && failedCount" class="steps-failed">{{ failedCount }} 失败</span></button>
              <ol v-if="selected?.id === run.id && stepsOpen && selected.steps.length" class="step-cards"><li v-for="step in selected.steps" :key="step.number" :data-kind="step.kind" :data-collapsible="step.detail && step.kind !== 'message' ? '1' : undefined"><header @click="step.detail && step.kind !== 'message' && toggleStep(step.number)"><span class="step-kind">{{ kindLabels[step.kind] ?? step.kind }}</span><code class="step-name">{{ step.title }}</code><span class="step-role">{{ roleLabels[step.role] ?? step.role }}</span><span class="badge" :data-status="step.status">{{ statusText(step.status) }}</span><span v-if="step.detail && step.kind !== 'message'" class="chev">{{ expandedSteps.has(step.number) ? '▾' : '▸' }}</span></header><p v-if="step.detail && step.kind !== 'message' && expandedSteps.has(step.number)" class="step-detail">{{ step.detail }}</p></li></ol>
              <div v-if="run.summary" class="reply-body" v-html="renderMd(run.summary)"></div>
              <p v-if="run.error" class="flow-error">{{ run.error }}</p>
              <div v-if="selected?.id === run.id && selected.prompt_tokens" class="run-meta"><span>输入 {{ selected.prompt_tokens.toLocaleString() }} tok</span><span>输出 {{ selected.completion_tokens.toLocaleString() }} tok</span><span>估算 ¥{{ selected.estimated_cost.toFixed(4) }}</span></div>
              <section v-if="selected?.id === run.id && selected.status === 'awaiting_approval'" class="approval-panel" aria-label="待审批动作">
                <h3>需要你的确认</h3><p>向导准备执行一项写入操作。可以修改参数后批准，也可以拒绝。</p>
                <label for="approval-payload">工具参数 · JSON</label>
                <textarea id="approval-payload" v-model="payload" rows="7" spellcheck="false" :disabled="busy" />
                <div class="approval-actions"><button type="button" :disabled="busy" @click="decide('approve')">批准并继续</button><button type="button" class="secondary" :disabled="busy" @click="decide('reject')">拒绝</button></div>
              </section>
            </div>
          </div>
        </template>
      </div>
      <form class="compose-dock" @submit.prevent="start">
        <textarea v-model="goal" maxlength="2000" rows="2" placeholder="今天帮你做些什么？建计划、拆任务、排复习…" :disabled="busy" @keydown.enter.exact.prevent="start" />
        <div class="dock-row">
          <button type="button" class="dock-plus" title="上传资料到知识库" :disabled="busy" @click="fileInput?.click()">+</button>
          <input ref="fileInput" type="file" hidden accept=".txt,.md,.pdf,.docx" @change="uploadFile">
          <div class="autonomy-inline">
            <button type="button" class="autonomy-pill" @click="autonomyMenuOpen = !autonomyMenuOpen"><i class="pill-icon">◈</i>{{ currentAutonomy.pill }}<span class="pill-chev">˅</span></button>
            <div v-if="autonomyMenuOpen" class="autonomy-menu">
              <button v-for="option in autonomyOptions" :key="option.id" type="button" :class="{ active: auth.user?.autonomy === option.id }" @click="pickAutonomy(option.id)"><b>{{ option.id }}</b><span>{{ option.title }}<small>{{ option.detail }}</small></span></button>
            </div>
          </div>
          <span class="dock-hint">Enter 开始 · Shift + Enter 换行</span>
          <button type="submit" class="dock-submit" :disabled="busy || !goal.trim()" title="开始运行">↑</button>
        </div>
      </form>
    </section>
    <nav class="mobile-nav" aria-label="工作区面板"><button type="button" :class="{ active: mobilePanel === 'history' }" @click="mobilePanel = 'history'">记录</button><button type="button" :class="{ active: mobilePanel === 'chat' }" @click="mobilePanel = 'chat'">探索</button></nav>
  </div>
</template>

<style scoped>
.agent-workspace{display:grid;grid-template-columns:248px minmax(0,1fr);height:calc(100vh - 72px);max-width:1480px;margin:auto;background:#f4f7ef;color:#173b36;overflow:hidden}.run-rail{background:#eef3e9;padding:28px 18px;border-color:#d6e1d5;overflow-y:auto;min-height:0}.run-rail{border-right:1px solid #d6e1d5}.rail-brand{display:flex;align-items:center;gap:10px;padding:2px 8px 28px}.brand-mark{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:#285d4e;color:#f3f7e9;font-weight:800;font-size:.72rem;letter-spacing:.04em}.rail-brand strong,.rail-brand small{display:block}.rail-brand strong{font-size:.9rem}.rail-brand small{color:#6a8278;font-size:.7rem;margin-top:3px}.new-run{width:100%;border:1px solid #7fa28d;border-radius:8px;background:#285d4e;color:#fff;padding:10px;cursor:pointer}.run-rail h2 span{float:right;color:#7c9688;font-variant-numeric:tabular-nums}.muted{color:#59736a}.prompt-chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:8px}.prompt-chips span{color:#6b8478;font-size:.72rem}.prompt-chips button{border:1px solid #c9dacd;border-radius:999px;background:#f6faf4;color:#3f7a63;padding:4px 12px;font:inherit;font-size:.72rem;cursor:pointer}.prompt-chips button:hover{background:#285d4e;color:#fff;border-color:#285d4e}.run-item{display:flex;align-items:center;gap:8px;width:100%;text-align:left;border:0;background:transparent;padding:10px 9px;margin-bottom:3px;border-radius:7px;color:inherit}
.run-item.active,.run-item:hover{background:#dfe9df}
.run-main{flex:1;min-width:0;cursor:pointer}
.run-goal-text{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;font-size:.78rem}
.run-item small{display:block;color:#6b8478;margin-top:4px;font-size:.68rem}
.run-ops{display:none;gap:2px;flex-shrink:0}
.run-item:hover .run-ops{display:flex}
.icon-op{display:grid;place-items:center;width:26px;height:26px;border:0;border-radius:6px;background:transparent;color:#6b8478;cursor:pointer;padding:0}
.icon-op:hover{background:#c9dcc9;color:#285d4e}
.icon-op.danger:hover{background:#f5e4df;color:#8c4638}.agent-main{display:flex;flex-direction:column;padding:0 clamp(24px,5vw,64px);max-width:960px;width:100%;justify-self:center;min-height:0}.connection{color:#6b8579;font-size:.72rem;padding-top:9px;white-space:nowrap}.connection i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#5a9d78;margin-right:5px}.agent-compose{display:flex;flex-direction:column;gap:10px;margin-top:28px}.agent-compose label,.approval-panel label{font-weight:650;font-size:.82rem}.agent-compose textarea{width:100%;font:inherit;border:1px solid #a9bfae;border-radius:8px;background:#fbfcf8;color:#173b36;padding:14px;resize:vertical;min-height:116px}.compose-foot{display:flex;justify-content:space-between;align-items:center;gap:12px}.compose-foot span{color:#789087;font-size:.7rem}.agent-compose button,.approval-actions button{border:0;border-radius:7px;background:#285d4e;color:#fff;padding:9px 17px;cursor:pointer}.agent-compose button:disabled,.approval-actions button:disabled{opacity:.55;cursor:wait}button{font:inherit}button:focus-visible,textarea:focus-visible,input:focus-visible{outline:3px solid #b58853;outline-offset:2px}.agent-error{color:#9b392c;margin:16px 0}.run-detail{margin-top:46px}.run-title{display:flex;align-items:baseline;justify-content:flex-start;gap:16px;border-bottom:1px solid #d6e1d5;padding-bottom:12px}.run-title h2{font-size:1.12rem;margin:0;flex:1}.run-title span{color:#466c5a;font-size:.78rem;white-space:nowrap}.step-list{list-style:none;padding:0;margin:8px 0 22px}.step-list li{display:flex;gap:15px;padding:14px 0;border-bottom:1px solid #e0e8df}.step-index{font-variant-numeric:tabular-nums;color:#789287;font-size:.82rem}.step-list strong{font-weight:650;font-size:.86rem}.step-list small{margin-left:10px;color:#70887d;font-size:.72rem}.step-list p{margin:6px 0 0;white-space:pre-wrap;line-height:1.55;font-size:.82rem}.run-summary{padding:12px 0;white-space:pre-wrap;line-height:1.65;font-size:.88rem}.approval-panel{padding:18px;background:#e4eee2;border:1px solid #c9dccb;border-radius:10px}.approval-panel h3{margin:0;font-size:1rem}.approval-panel p{margin:0 0 5px;color:#466156;font-size:.82rem}.approval-panel textarea{font-family:ui-monospace,monospace;font-size:.8rem}.approval-actions{display:flex;gap:8px;flex-wrap:wrap}.approval-actions .secondary{background:transparent;color:#285d4e;border:1px solid #7d9d8b}.context-block{padding:14px 8px;border-bottom:1px solid #d8e3d8}.context-block span,.context-block strong{display:block}.context-block span{font-size:.7rem;color:#789087;margin-bottom:5px}.context-block strong{font-size:.78rem;line-height:1.45;font-weight:600}.context-note{margin:18px 8px;padding:12px;background:#e1eddf;border-radius:8px;color:#466156;font-size:.76rem;line-height:1.55}.mobile-nav{display:none}
.autonomy-panel{display:grid;gap:12px;margin-top:24px;padding:14px 16px;border:1px solid #d3e1d4;border-radius:10px;background:#edf4eb}.autonomy-panel>div:first-child{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.autonomy-panel strong{font-size:.82rem}.autonomy-panel>div:first-child span{color:#668075;font-size:.72rem}.autonomy-options{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.autonomy-options button{display:grid;grid-template-columns:auto 1fr;gap:2px 7px;padding:9px;border:1px solid transparent;border-radius:7px;color:#527265;background:transparent;text-align:left;cursor:pointer}.autonomy-options button:hover{background:#e0ece0}.autonomy-options button.active{border-color:#8eb39b;background:#f9fcf6;color:#285d4e;box-shadow:0 3px 10px rgba(40,93,78,.08)}.autonomy-options b{grid-row:span 2;color:#285d4e;font-size:.72rem}.autonomy-options span{font-size:.74rem;font-weight:650}.autonomy-options small{grid-column:2;color:#789087;font-size:.64rem;line-height:1.25}
@media(max-width:900px){.agent-workspace{display:flex;flex-direction:column;height:auto;min-height:calc(100vh - 72px);overflow:visible}.run-rail{display:none}.panel-history .run-rail{display:block;border:0;min-height:calc(100vh - 124px);padding:22px 20px}.panel-history .agent-main{display:none}.panel-chat .agent-main{display:block}.agent-main{padding:26px 20px 76px;max-width:none}.mobile-nav{position:fixed;display:grid;grid-template-columns:repeat(2,1fr);bottom:0;left:0;right:0;height:54px;background:#f7faf3;border-top:1px solid #d6e1d5;z-index:5}.mobile-nav button{border:0;background:transparent;color:#6c8479;font-size:.76rem}.mobile-nav button.active{color:#285d4e;font-weight:700}}
.cancel-button{border:1px solid #9b6b5f;background:transparent;color:#8c4638;border-radius:7px;padding:5px 10px;cursor:pointer}.live-events{display:grid;gap:5px;margin:18px 0;padding:12px 14px;background:#f0f4ed;border-radius:10px}.live-events p{margin:0;display:flex;gap:10px;font-size:.9rem}.live-events small{color:#658476;min-width:52px}
.run-item[data-status="awaiting_approval"]{border-left:3px solid #b7791f;background:#fdf6e9}.run-item[data-status="awaiting_approval"] small{color:#8a6d2f;font-weight:650}
.rail-group{display:flex;align-items:center;gap:7px;width:calc(100% - 16px);margin:28px 8px 12px;padding:0;border:0;background:transparent;color:#506b5e;font-size:.75rem;font-weight:650;letter-spacing:.03em;cursor:pointer;text-align:left;font-family:inherit}
.rail-group:hover{color:#285d4e}
.rail-group span:last-child{margin-left:auto;color:#7c9688;font-variant-numeric:tabular-nums;font-weight:400}
.group-chev{color:#8aa195;font-size:.62rem;width:10px;flex-shrink:0}
/* ── Agent 输出流(参考 WorkBuddy 消息流:卡片 + 徽章 + 时间线 + 元信息)── */
.step-cards{list-style:none;display:grid;gap:8px;margin:18px 0 0;padding:0}
.step-cards li{border:1px solid #dbe6da;border-radius:10px;background:#fbfdf9}
.step-cards li[data-kind="handoff"]{border-style:dashed;border-color:#c4d6c6;background:transparent}
.step-cards header{display:flex;align-items:center;gap:8px;padding:9px 12px}
.step-kind{flex-shrink:0;font-size:.66rem;color:#527265;background:#e7f0e6;padding:2px 7px;border-radius:5px;font-weight:650}
.step-name{font-size:.76rem;color:#24483f;background:#eef4ec;padding:2px 8px;border-radius:5px;font-family:ui-monospace,Consolas,"Courier New",monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.step-role{font-size:.7rem;color:#6b8478;flex-shrink:0}
.badge{margin-left:auto;flex-shrink:0;font-size:.66rem;padding:2px 9px;border-radius:999px;background:#e7f0e6;color:#3d6a57;font-weight:600}
.badge[data-status="completed"]{background:#e1efe4;color:#2f6b58}
.badge[data-status="failed"],.badge[data-status="rejected"]{background:#f5e4df;color:#8c4638}
.badge[data-status="running"],.badge[data-status="awaiting_approval"]{background:#f4ead3;color:#8a6d2f}
.step-detail{margin:0;padding:0 12px 11px;font-size:.8rem;color:#41605a;line-height:1.7;white-space:pre-wrap;word-break:break-word}
.final-reply{margin-top:18px;padding:14px 16px;border:1px solid #cfe0d2;border-radius:10px;background:#f2f8f0}
.final-reply h3{margin:0 0 8px;font-size:.72rem;color:#4b8f73;letter-spacing:.1em}
.final-reply p{margin:0;font-size:.88rem;line-height:1.85;white-space:pre-wrap;color:#22453c}
.event-stream{list-style:none;margin:16px 0 4px;padding:2px 0 2px 16px;border-left:2px solid #d8e4d8;display:grid;gap:2px}
.event-stream li{position:relative;display:flex;gap:9px;padding:3px 0;font-size:.76rem;color:#4f6a5e}
.event-dot{position:absolute;left:-19.5px;top:9px;width:7px;height:7px;border-radius:50%;background:#9db8a6}
.event-stream li:last-child .event-dot{background:#285d4e;box-shadow:0 0 0 3px #e1eee2}
.event-stream li[data-type="done"] span{color:#2f6b58;font-weight:650}
.event-stream li[data-type="approval"] span{color:#8a6d2f;font-weight:650}
.run-meta{display:flex;gap:14px;justify-content:flex-end;margin-top:14px;padding:8px 12px;border-radius:8px;background:#eef3ec;color:#5f756d;font-size:.7rem;font-variant-numeric:tabular-nums}
.step-cards li[data-collapsible] header{cursor:pointer;user-select:none}
.step-cards li[data-collapsible]:hover{border-color:#b9cfbc;background:#f6faf4}
.chev{flex-shrink:0;width:14px;text-align:center;color:#7c9688;font-size:.7rem}
/* ── markdown 渲染(向导回复与学习对话共用)── */
.reply-body{font-size:.88rem;line-height:1.9;color:#22453c}
.reply-body>:first-child{margin-top:0}
.reply-body>:last-child{margin-bottom:0}
.reply-body h1,.reply-body h2,.reply-body h3,.reply-body h4{margin:1.2em 0 .45em;font-family:"Noto Serif SC",Georgia,serif;font-weight:600;line-height:1.4}
.reply-body h1{font-size:1.18rem}.reply-body h2{font-size:1.06rem}.reply-body h3{font-size:.96rem}.reply-body h4{font-size:.88rem}
.reply-body p{margin:.55em 0}
.reply-body ul,.reply-body ol{margin:.45em 0;padding-left:1.45em}
.reply-body li{margin:.28em 0}
.reply-body li::marker{color:#4b8f73}
.reply-body code{background:#e7f0e6;color:#2f6b58;padding:.12em .45em;border-radius:5px;font-size:.82em;font-family:ui-monospace,Consolas,"Courier New",monospace}
.reply-body pre{background:#eef4ec;border:1px solid #d8e4d8;border-radius:8px;padding:11px 13px;overflow-x:auto;margin:.7em 0}
.reply-body pre code{background:transparent;padding:0;color:inherit}
.reply-body strong{color:#12332c;font-weight:700}
.reply-body blockquote{margin:.6em 0;padding:.2em 1em;border-left:3px solid #cfe0d2;color:#527265}
.chat-message .reply-body{font-size:.82rem;line-height:1.7}
.plain-text{white-space:pre-wrap}
.chat-message.pending .plain-text{color:#527265;animation:thinking 1.2s ease-in-out infinite}
.chat-message.failed{border-color:#e0c4bc;background:#fbf3f0}
.chat-message.failed .plain-text{color:#8c4638;font-size:.78rem}
@keyframes thinking{0%,100%{opacity:.45}50%{opacity:1}}
.steps-toggle{display:flex;align-items:center;gap:9px;width:100%;margin-top:18px;padding:10px 13px;border:1px solid #dbe6da;border-radius:10px;background:#f6faf4;color:#2f6b58;font:inherit;font-size:.8rem;cursor:pointer;text-align:left}
.steps-toggle:hover{background:#eef5ec}
.steps-toggle strong{font-weight:650}
.steps-toggle .chev{color:#4b8f73}
.steps-meta{color:#6b8478;font-size:.72rem}
.steps-failed{margin-left:auto;color:#8c4638;font-size:.7rem;background:#f5e4df;padding:2px 9px;border-radius:999px;font-weight:600}
.steps-section .step-cards{margin-top:8px}
.task-list{display:grid;gap:2px}
.task-item{display:grid;grid-template-columns:auto 1fr;gap:3px 8px;width:100%;text-align:left;border:0;background:transparent;padding:8px 9px;border-radius:7px;cursor:pointer;color:inherit;font:inherit}
.task-item:hover{background:#dfe9df}
.task-check{width:14px;height:14px;border:1.5px solid #7fa28d;border-radius:50%;margin-top:2px;grid-row:span 2}
.task-item:hover .task-check{background:#cfe0d2;border-color:#4b8f73}
.task-title{font-size:.76rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.task-item small{color:#6b8478;font-size:.66rem}
.task-item small.overdue{color:#a04b3a;font-weight:650}
.task-ops{display:none;gap:4px;align-items:center;grid-column:3;grid-row:span 2}
.task-item:hover .task-ops{display:flex}
.task-op{border:0;background:#e8efe6;color:#527265;border-radius:5px;padding:2px 6px;font-size:.62rem;cursor:pointer;font-family:inherit}
.task-op:hover{background:#285d4e;color:#fff}
.task-op.danger{color:#8c4638;background:#f5e4df}
.task-op.danger:hover{background:#8c4638;color:#fff}</style>
<style scoped>
.run-flow{flex:1;min-height:0;overflow-y:auto;display:grid;gap:14px;align-content:start;padding:20px 2px}
.flow-empty{margin:1.5rem 0;color:#678075;font-size:.86rem;line-height:1.8}
.flow-row{display:flex;gap:10px;align-items:flex-start}
.flow-row.user{flex-direction:row-reverse}
.flow-avatar{flex-shrink:0;display:grid;place-items:center;width:34px;height:34px;border-radius:9px;font-size:.68rem;font-weight:750}
.flow-avatar.mm{background:#285d4e;color:#f3f7e9}
.flow-row.user .flow-avatar{background:#e1eee2;color:#2f6b58}
.flow-bubble{max-width:min(82%,660px);padding:12px 15px;border:1px solid #d8e4d8;border-radius:10px;background:#fbfdf9;display:grid;gap:9px}
.user-bubble{background:#e9f2ea;border-color:#cfe0d2;font-size:.86rem;font-weight:600;line-height:1.7;white-space:pre-wrap}
.wizard-bubble{display:grid}
.wizard-head{display:flex;align-items:center;gap:9px}
.flow-meta{color:#6b8478;font-size:.7rem;font-variant-numeric:tabular-nums}
.wizard-head .cancel-button{margin-left:auto}
.flow-error{margin:0;color:#9b392c;font-size:.8rem}
.upload-note{margin:10px 0 0;padding:9px 13px;border:1px solid #cfe0d2;border-radius:8px;background:#f0f7ee;color:#2f6b58;font-size:.78rem}
.compose-dock{display:grid;gap:8px;padding:14px 0 18px;border-top:1px solid #d6e1d5;flex-shrink:0}
.dock-row{display:flex;gap:8px;align-items:flex-end}
.dock-plus{flex-shrink:0;width:46px;height:46px;border:1px solid #c9dacd;border-radius:9px;background:#f6faf4;color:#3f7a63;font-size:1.25rem;cursor:pointer;padding:0}
.dock-plus:hover{background:#285d4e;color:#fff;border-color:#285d4e}
.dock-row textarea{flex:1;min-width:0;min-height:46px;max-height:130px;font:inherit;border:1px solid #a9bfae;border-radius:9px;background:#fbfcf8;color:#173b36;padding:12px 14px;resize:none}
.autonomy-inline{position:relative;flex-shrink:0}
.autonomy-pill{display:inline-flex;align-items:center;gap:6px;height:46px;border:1px solid #c9dacd;border-radius:9px;background:#f6faf4;color:#3f7a63;padding:0 13px;font:inherit;font-size:.72rem;font-weight:650;cursor:pointer;white-space:nowrap}
.autonomy-pill:hover{background:#e8f2e8}
.pill-icon{font-style:normal;font-size:.72rem}
.pill-chev{color:#7c9688;font-size:.6rem}
.autonomy-menu{position:absolute;bottom:calc(100% + 8px);left:0;z-index:6;display:grid;gap:2px;min-width:260px;padding:6px;border:1px solid #d3e1d4;border-radius:10px;background:#fbfdf9;box-shadow:0 10px 30px rgba(23,59,54,.14)}
.autonomy-menu button{display:grid;grid-template-columns:auto 1fr;gap:2px 9px;padding:9px 10px;border:0;border-radius:7px;background:transparent;color:#527265;text-align:left;cursor:pointer;font:inherit}
.autonomy-menu button:hover{background:#eaf2e9}
.autonomy-menu button.active{background:#e1efe4;color:#285d4e}
.autonomy-menu b{font-size:.72rem}
.autonomy-menu span{font-size:.74rem;font-weight:650}
.autonomy-menu small{grid-column:2;color:#789087;font-size:.66rem}
.dock-submit{flex-shrink:0;height:46px;border:0;border-radius:9px;background:#285d4e;color:#fff;padding:0 20px;cursor:pointer;font:inherit;font-weight:650}
.dock-submit:disabled{opacity:.55;cursor:wait}
.dock-hint{margin:0;color:#789087;font-size:.68rem}
@media(max-width:900px){.agent-main{padding:0 20px;height:calc(100vh - 126px)}.compose-dock{padding:12px 0 12px}.autonomy-pill{padding:0 9px}}
</style>
