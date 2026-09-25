<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

type Status = 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'rejected'
interface Run { id: string; goal: string; status: Status; current_step: number; role: string; summary: string | null; error: string | null; prompt_tokens: number; completion_tokens: number; estimated_cost: number }
interface Step { number: number; title: string; detail: string | null; role: string; status: string }
interface Approval { id: string; status: string; payload: Record<string, unknown> }
interface Detail extends Run { steps: Step[]; approvals: Approval[] }
interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string }

const runs = ref<Run[]>([])
const selected = ref<Detail | null>(null)
const goal = ref('')
const payload = ref('')
const busy = ref(false)
const error = ref('')
const conversationId = ref<string | null>(null)
const chatMessages = ref<ChatMessage[]>([])
const chatInput = ref('')
const liveEvents = ref<{ id: number; type: string; text: string }[]>([])
let stream: EventSource | null = null
const mobilePanel = ref<'history' | 'chat' | 'context'>('chat')
const quickPrompts = ['拆解本周目标', '复盘最近进度', '安排一次专注']
const auth = useAuthStore()
const autonomyOptions = [
  { id: 'L0', title: '步步确认', detail: '所有写入都先询问' },
  { id: 'L1', title: '低风险自动', detail: '待办与复习自动执行' },
  { id: 'L2', title: '高自主', detail: '高风险动作仍需确认' },
]
const roleLabels: Record<string, string> = { Planner: '规划者', Executor: '执行者', Reflector: '复盘者', Curator: '记忆官', Scout: '向导' }
const kindLabels: Record<string, string> = { tool: '工具', message: '回复', handoff: '委派' }
function statusText(status: string) { return (labels as Record<string, string>)[status] ?? status }

async function setAutonomy(level: string) {
  try { await auth.setAutonomy(level) } catch (cause) { error.value = cause instanceof Error ? cause.message : '自主档位更新失败' }
}

function applyPrompt(prompt: string) {
  goal.value = prompt
  mobilePanel.value = 'chat'
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
  selected.value = await request<Detail>(`/${id}`)
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
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法启动运行' }
  finally { busy.value = false }
}

function watchRun(id: string) {
  stream?.close(); liveEvents.value = []
  stream = new EventSource(`/api/agent/runs/${id}/stream`, { withCredentials: true })
  const handle = (event: MessageEvent) => {
    const payload = JSON.parse(event.data) as Record<string, unknown>
    liveEvents.value.push({ id: Number(event.lastEventId || Date.now()), type: event.type, text: String(payload.title ?? payload.status ?? payload.summary ?? payload.tool ?? '运行事件') })
    if (event.type === 'done' || event.type === 'approval') void refresh(id)
  }
  for (const type of ['status', 'phase', 'step', 'approval', 'done']) stream.addEventListener(type, handle)
  stream.onerror = () => { if (['completed', 'failed', 'cancelled'].includes(selected.value?.status ?? '')) stream?.close() }
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

async function loadConversation() {
  const response = await fetch('/api/conversations', { credentials: 'include' })
  if (!response.ok) return
  const body = await response.json()
  let item = body.data?.[0]
  if (!item) {
    const created = await fetch('/api/conversations', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: '学习对话' }) }).then(r => r.json())
    item = created.data
  }
  conversationId.value = item.id
  const detail = await fetch(`/api/conversations/${item.id}`, { credentials: 'include' }).then(r => r.json())
  chatMessages.value = detail.data.messages
}

async function sendChat() {
  if (!conversationId.value || !chatInput.value.trim() || busy.value) return
  const content = chatInput.value.trim(); chatInput.value = ''; busy.value = true
  try {
    const response = await fetch(`/api/conversations/${conversationId.value}/messages`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content }) })
    const body = await response.json(); if (!response.ok) throw new Error(body.error?.message ?? '发送失败')
    chatMessages.value.push({ id: `user-${Date.now()}`, role: 'user', content }, body.data.message)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '发送失败' }
  finally { busy.value = false }
}

let pollTimer: number | undefined
async function poll() {
  // 兜底轮询:SSE 断线、页面刷新后的挂起运行、审批状态变化都能被看到
  try {
    runs.value = await request<Run[]>('')
    const watching = runs.value.find(item => item.id === selected.value?.id)
    if (watching && ['queued', 'running', 'awaiting_approval'].includes(watching.status)) await open(watching.id)
  } catch { /* 轮询失败静默,下个周期重试 */ }
}

onMounted(() => {
  void Promise.all([refresh(), loadConversation()]).catch(cause => { error.value = cause instanceof Error ? cause.message : '加载失败' })
  pollTimer = window.setInterval(() => void poll(), 6000)
})
onUnmounted(() => { stream?.close(); if (pollTimer) window.clearInterval(pollTimer) })
</script>

<template>
  <div class="agent-workspace" :class="`panel-${mobilePanel}`">
    <aside class="run-rail" aria-label="运行记录">
      <div class="rail-brand"><span class="brand-mark">MM</span><div><strong>山程向导</strong><small>学习节奏工作台</small></div></div>
      <button type="button" class="new-run" @click="goal = ''; mobilePanel = 'chat'">新建运行</button>
      <h2>最近运行 <span>{{ runs.length }}</span></h2>
      <div class="quick-prompts"><button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="applyPrompt(prompt)">{{ prompt }}</button></div>
      <p v-if="!runs.length" class="muted">还没有运行记录</p>
      <button v-for="run in runs" :key="run.id" type="button" class="run-item" :class="{ active: selected?.id === run.id }" :data-status="run.status" @click="open(run.id)">
        <span>{{ run.goal }}</span><small>{{ labels[run.status] }}</small>
      </button>
    </aside>
    <section class="agent-main">
      <header class="agent-heading"><div><h1>学习向导</h1><p>询问、复盘与深入理解</p></div><span class="connection"><i></i> 本地工作区</span></header>
      <section class="autonomy-panel" aria-label="自主档位"><div><strong>自主档位</strong><span>决定写入动作何时需要确认</span></div><div class="autonomy-options"><button v-for="option in autonomyOptions" :key="option.id" type="button" :class="{ active: auth.user?.autonomy === option.id }" @click="setAutonomy(option.id)"><b>{{ option.id }}</b><span>{{ option.title }}</span><small>{{ option.detail }}</small></button></div></section>
      <form class="agent-compose" @submit.prevent="start">
        <label for="agent-goal">这次想做什么？</label>
        <textarea id="agent-goal" v-model="goal" maxlength="2000" rows="3" placeholder="问一个问题，或说说你卡在哪里…" :disabled="busy" @keydown.enter.exact.prevent="start" />
        <div class="compose-foot"><span>Enter 开始 · Shift + Enter 换行</span><button type="submit" :disabled="busy || !goal.trim()">{{ busy ? '处理中…' : '开始运行' }}</button></div>
      </form>
      <p v-if="error" class="agent-error" role="alert">{{ error }}</p>
      <div v-if="selected" class="run-detail">
        <div class="run-title"><h2>{{ selected.goal }}</h2><span>{{ labels[selected.status] }}</span><button v-if="['queued','running'].includes(selected.status)" type="button" class="cancel-button" :disabled="busy" @click="cancel">中断</button></div>
        <ol v-if="liveEvents.length" class="event-stream" aria-live="polite"><li v-for="item in liveEvents" :key="item.id" :data-type="item.type"><i class="event-dot"></i><span>{{ item.text }}</span></li></ol>
        <ol class="step-cards"><li v-for="step in selected.steps" :key="step.number" :data-kind="step.kind"><header><span class="step-kind">{{ kindLabels[step.kind] ?? step.kind }}</span><code class="step-name">{{ step.title }}</code><span class="step-role">{{ roleLabels[step.role] ?? step.role }}</span><span class="badge" :data-status="step.status">{{ statusText(step.status) }}</span></header><p v-if="step.detail && step.kind !== 'message'" class="step-detail">{{ step.detail }}</p></li></ol>
        <section v-if="selected.summary" class="final-reply" aria-label="向导回复"><h3>向导回复</h3><p>{{ selected.summary }}</p></section>
        <div v-if="selected.prompt_tokens" class="run-meta"><span>输入 {{ selected.prompt_tokens.toLocaleString() }} tok</span><span>输出 {{ selected.completion_tokens.toLocaleString() }} tok</span><span>估算 ¥{{ selected.estimated_cost.toFixed(4) }}</span></div>
        <p v-if="selected.error" class="agent-error">{{ selected.error }}</p>
        <section v-if="selected.status === 'awaiting_approval'" class="approval-panel" aria-label="待审批动作">
          <h3>需要你的确认</h3><p>向导准备执行一项写入操作。可以修改参数后批准，也可以拒绝。</p>
          <label for="approval-payload">工具参数 · JSON</label>
          <textarea id="approval-payload" v-model="payload" rows="7" spellcheck="false" :disabled="busy" />
          <div class="approval-actions"><button type="button" :disabled="busy" @click="decide('approve')">批准并继续</button><button type="button" class="secondary" :disabled="busy" @click="decide('reject')">拒绝</button></div>
        </section>
      </div>
      <section class="chat-panel" aria-label="学习对话">
        <div class="chat-heading"><h2>学习对话</h2><span>消息会保存到当前账户</span></div>
        <div class="chat-messages"><p v-if="!chatMessages.length" class="muted">从一个学习问题开始。</p><p v-for="message in chatMessages" :key="message.id" :class="['chat-message', message.role]"><strong>{{ message.role === 'user' ? '你' : '向导' }}</strong>{{ message.content }}</p></div>
        <form class="chat-compose" @submit.prevent="sendChat"><input v-model="chatInput" maxlength="10000" placeholder="问问你的学习向导…" :disabled="busy" /><button type="submit" :disabled="busy || !chatInput.trim()">发送</button></form>
      </section>
    </section>
    <aside class="context-rail" aria-label="当前上下文">
      <h2>当前上下文</h2><div class="context-block"><span>运行状态</span><strong>{{ selected ? labels[selected.status] : '等待开始' }}</strong></div>
      <div class="context-block"><span>观察范围</span><strong>计划 · 待办 · 今日任务</strong></div>
      <div class="context-block"><span>当前角色</span><strong>{{ selected ? (roleLabels[selected.role] ?? selected.role) : '等待分派' }}</strong></div><div class="context-block"><span>审批策略</span><strong>{{ auth.user?.autonomy === 'L0' ? '所有写入需确认' : auth.user?.autonomy === 'L1' ? '低风险自动执行' : '仅高风险需确认' }}</strong></div>
      <div v-if="selected?.status === 'awaiting_approval'" class="context-note">向导正在等待你的决定。批准前可以修改参数。</div>
    </aside>
    <nav class="mobile-nav" aria-label="工作区面板"><button type="button" :class="{ active: mobilePanel === 'history' }" @click="mobilePanel = 'history'">记录</button><button type="button" :class="{ active: mobilePanel === 'chat' }" @click="mobilePanel = 'chat'">探索</button><button type="button" :class="{ active: mobilePanel === 'context' }" @click="mobilePanel = 'context'">上下文</button></nav>
  </div>
</template>

<style scoped>
.agent-workspace{display:grid;grid-template-columns:248px minmax(0,1fr) 238px;min-height:calc(100vh - 72px);max-width:1480px;margin:auto;background:#f4f7ef;color:#173b36}.run-rail,.context-rail{background:#eef3e9;padding:28px 18px;border-color:#d6e1d5}.run-rail{border-right:1px solid #d6e1d5}.context-rail{border-left:1px solid #d6e1d5}.rail-brand{display:flex;align-items:center;gap:10px;padding:2px 8px 28px}.brand-mark{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:#285d4e;color:#f3f7e9;font-weight:800;font-size:.72rem;letter-spacing:.04em}.rail-brand strong,.rail-brand small{display:block}.rail-brand strong{font-size:.9rem}.rail-brand small{color:#6a8278;font-size:.7rem;margin-top:3px}.new-run{width:100%;border:1px solid #7fa28d;border-radius:8px;background:#285d4e;color:#fff;padding:10px;cursor:pointer}.run-rail h2,.context-rail h2{font-size:.75rem;letter-spacing:.03em;margin:28px 8px 12px;color:#506b5e}.run-rail h2 span{float:right;color:#7c9688;font-variant-numeric:tabular-nums}.muted{color:#59736a}.quick-prompts{display:grid;gap:2px}.quick-prompts button{border:0;background:transparent;color:#5a7469;padding:8px;text-align:left;border-radius:6px;cursor:pointer;font-size:.78rem}.quick-prompts button:hover{background:#dfe9df;color:#285d4e}.run-item{display:block;width:100%;text-align:left;border:0;background:transparent;padding:11px 9px;margin-bottom:3px;border-radius:7px;color:inherit;cursor:pointer}.run-item.active,.run-item:hover{background:#dfe9df}.run-item span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;font-size:.78rem}.run-item small{display:block;color:#6b8478;margin-top:4px;font-size:.68rem}.agent-main{padding:34px clamp(24px,5vw,64px);max-width:920px;width:100%;justify-self:center}.agent-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;border-bottom:1px solid #d6e1d5;padding-bottom:22px}.agent-heading h1{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(2rem,4vw,3.7rem);font-weight:500;line-height:1.08;margin:0 0 7px}.agent-heading p{color:#59736a;margin:0;font-size:.9rem}.connection{color:#6b8579;font-size:.72rem;padding-top:9px;white-space:nowrap}.connection i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#5a9d78;margin-right:5px}.agent-compose{display:flex;flex-direction:column;gap:10px;margin-top:28px}.agent-compose label,.approval-panel label{font-weight:650;font-size:.82rem}.agent-compose textarea{width:100%;font:inherit;border:1px solid #a9bfae;border-radius:8px;background:#fbfcf8;color:#173b36;padding:14px;resize:vertical;min-height:116px}.compose-foot{display:flex;justify-content:space-between;align-items:center;gap:12px}.compose-foot span{color:#789087;font-size:.7rem}.agent-compose button,.approval-actions button{border:0;border-radius:7px;background:#285d4e;color:#fff;padding:9px 17px;cursor:pointer}.agent-compose button:disabled,.approval-actions button:disabled{opacity:.55;cursor:wait}button{font:inherit}button:focus-visible,textarea:focus-visible,input:focus-visible{outline:3px solid #b58853;outline-offset:2px}.agent-error{color:#9b392c;margin:16px 0}.run-detail{margin-top:46px}.run-title{display:flex;align-items:baseline;justify-content:flex-start;gap:16px;border-bottom:1px solid #d6e1d5;padding-bottom:12px}.run-title h2{font-size:1.12rem;margin:0;flex:1}.run-title span{color:#466c5a;font-size:.78rem;white-space:nowrap}.step-list{list-style:none;padding:0;margin:8px 0 22px}.step-list li{display:flex;gap:15px;padding:14px 0;border-bottom:1px solid #e0e8df}.step-index{font-variant-numeric:tabular-nums;color:#789287;font-size:.82rem}.step-list strong{font-weight:650;font-size:.86rem}.step-list small{margin-left:10px;color:#70887d;font-size:.72rem}.step-list p{margin:6px 0 0;white-space:pre-wrap;line-height:1.55;font-size:.82rem}.run-summary{padding:12px 0;white-space:pre-wrap;line-height:1.65;font-size:.88rem}.approval-panel{padding:18px;background:#e4eee2;border:1px solid #c9dccb;border-radius:10px}.approval-panel h3{margin:0;font-size:1rem}.approval-panel p{margin:0 0 5px;color:#466156;font-size:.82rem}.approval-panel textarea{font-family:ui-monospace,monospace;font-size:.8rem}.approval-actions{display:flex;gap:8px;flex-wrap:wrap}.approval-actions .secondary{background:transparent;color:#285d4e;border:1px solid #7d9d8b}.context-rail h2{margin-top:4px}.context-block{padding:14px 8px;border-bottom:1px solid #d8e3d8}.context-block span,.context-block strong{display:block}.context-block span{font-size:.7rem;color:#789087;margin-bottom:5px}.context-block strong{font-size:.78rem;line-height:1.45;font-weight:600}.context-note{margin:18px 8px;padding:12px;background:#e1eddf;border-radius:8px;color:#466156;font-size:.76rem;line-height:1.55}.mobile-nav{display:none}
.autonomy-panel{display:grid;gap:12px;margin-top:24px;padding:14px 16px;border:1px solid #d3e1d4;border-radius:10px;background:#edf4eb}.autonomy-panel>div:first-child{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.autonomy-panel strong{font-size:.82rem}.autonomy-panel>div:first-child span{color:#668075;font-size:.72rem}.autonomy-options{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.autonomy-options button{display:grid;grid-template-columns:auto 1fr;gap:2px 7px;padding:9px;border:1px solid transparent;border-radius:7px;color:#527265;background:transparent;text-align:left;cursor:pointer}.autonomy-options button:hover{background:#e0ece0}.autonomy-options button.active{border-color:#8eb39b;background:#f9fcf6;color:#285d4e;box-shadow:0 3px 10px rgba(40,93,78,.08)}.autonomy-options b{grid-row:span 2;color:#285d4e;font-size:.72rem}.autonomy-options span{font-size:.74rem;font-weight:650}.autonomy-options small{grid-column:2;color:#789087;font-size:.64rem;line-height:1.25}
.chat-panel{margin-top:42px;border-top:1px solid #d6e1d5;padding-top:22px}.chat-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px}.chat-heading h2{font-size:1.05rem;margin:0}.chat-heading span{font-size:.72rem;color:#6f887c}.chat-messages{display:grid;gap:8px;margin:16px 0;min-height:40px}.chat-message{display:grid;gap:4px;max-width:75%;margin:0;padding:10px 12px;border:1px solid #d8e4d8;border-radius:9px;line-height:1.55;white-space:pre-wrap;font-size:.82rem}.chat-message.user{justify-self:end;background:#e1eee2}.chat-message.assistant{background:#fbfcf8}.chat-message strong{font-size:.7rem;color:#527265}.chat-compose{display:flex;flex-direction:row;gap:7px}.chat-compose input{min-width:0;flex:1;border:1px solid #a9bfae;border-radius:7px;padding:10px;font:inherit;background:#fbfcf8}.chat-compose button{border:0;border-radius:7px;background:#285d4e;color:#fff;padding:0 16px;cursor:pointer}.chat-compose button:disabled{opacity:.55}.cancel-button{border:1px solid #9b6b5f;background:transparent;color:#8c4638;border-radius:7px;padding:5px 10px;cursor:pointer}.live-events{display:grid;gap:5px;margin:15px 0;padding:11px 13px;background:#edf4eb;border:1px solid #d8e4d8;border-radius:8px}.live-events p{margin:0;display:flex;gap:10px;font-size:.8rem}.live-events small{color:#658476;min-width:52px}
@media(max-width:900px){.agent-workspace{display:flex;flex-direction:column;min-height:calc(100vh - 72px)}.run-rail,.context-rail{display:none}.panel-history .run-rail,.panel-context .context-rail{display:block;border:0;min-height:calc(100vh - 124px);padding:22px 20px}.panel-history .agent-main,.panel-context .agent-main{display:none}.panel-context .context-rail{order:0}.panel-chat .agent-main{display:block}.agent-main{padding:26px 20px 76px;max-width:none}.mobile-nav{position:fixed;display:grid;grid-template-columns:repeat(3,1fr);bottom:0;left:0;right:0;height:54px;background:#f7faf3;border-top:1px solid #d6e1d5;z-index:5}.mobile-nav button{border:0;background:transparent;color:#6c8479;font-size:.76rem}.mobile-nav button.active{color:#285d4e;font-weight:700}.context-rail{border:0}.agent-heading h1{font-size:2.3rem}}
.chat-panel{margin-top:56px;border-top:1px solid #d3e1d5;padding-top:24px}.chat-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px}.chat-heading h2{font-size:1.25rem;margin:0}.chat-heading span{font-size:.8rem;color:#63786e}.chat-messages{display:grid;gap:10px;margin:18px 0;min-height:48px}.chat-message{display:grid;gap:4px;max-width:75%;margin:0;padding:10px 12px;border-radius:10px;line-height:1.55;white-space:pre-wrap}.chat-message.user{justify-self:end;background:#dfece2}.chat-message.assistant{background:#f0f4ed}.chat-message strong{font-size:.75rem;color:#527265}.chat-compose{display:flex;flex-direction:row;gap:8px}.chat-compose input{min-width:0;flex:1;border:1px solid #a6bdb0;border-radius:8px;padding:11px;font:inherit}.chat-compose button{border:0;border-radius:8px;background:#285d4e;color:#fff;padding:0 18px;cursor:pointer}.chat-compose button:disabled{opacity:.55}
.cancel-button{border:1px solid #9b6b5f;background:transparent;color:#8c4638;border-radius:7px;padding:5px 10px;cursor:pointer}.live-events{display:grid;gap:5px;margin:18px 0;padding:12px 14px;background:#f0f4ed;border-radius:10px}.live-events p{margin:0;display:flex;gap:10px;font-size:.9rem}.live-events small{color:#658476;min-width:52px}
.run-item[data-status="awaiting_approval"]{border-left:3px solid #b7791f;background:#fdf6e9}.run-item[data-status="awaiting_approval"] small{color:#8a6d2f;font-weight:650}
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
.run-meta{display:flex;gap:14px;justify-content:flex-end;margin-top:14px;padding:8px 12px;border-radius:8px;background:#eef3ec;color:#5f756d;font-size:.7rem;font-variant-numeric:tabular-nums}</style>
