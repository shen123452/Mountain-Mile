<script setup lang="ts">
import { onMounted, ref } from 'vue'

type Status = 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'rejected'
interface Run { id: string; goal: string; status: Status; current_step: number; summary: string | null; error: string | null }
interface Step { number: number; title: string; detail: string | null; status: string }
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
  payload.value = pending ? JSON.stringify(pending.payload, null, 2) : ''
}

async function start() {
  if (!goal.value.trim() || busy.value) return
  busy.value = true; error.value = ''
  try {
    const run = await request<Run>('', { method: 'POST', body: JSON.stringify({ goal: goal.value.trim() }) })
    goal.value = ''
    await refresh(run.id)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法启动运行' }
  finally { busy.value = false }
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

onMounted(() => { void Promise.all([refresh(), loadConversation()]).catch(cause => { error.value = cause instanceof Error ? cause.message : '加载失败' }) })
</script>

<template>
  <div class="agent-workspace">
    <aside class="run-rail" aria-label="运行记录">
      <h2>运行记录</h2>
      <p v-if="!runs.length" class="muted">还没有运行记录</p>
      <button v-for="run in runs" :key="run.id" type="button" class="run-item" :class="{ active: selected?.id === run.id }" @click="open(run.id)">
        <span>{{ run.goal }}</span><small>{{ labels[run.status] }}</small>
      </button>
    </aside>
    <section class="agent-main">
      <header class="agent-heading"><h1>学习向导</h1><p>说出你想安排的学习事务，向导会查询信息并提出行动。</p></header>
      <form class="agent-compose" @submit.prevent="start">
        <label for="agent-goal">这次想做什么？</label>
        <textarea id="agent-goal" v-model="goal" maxlength="2000" rows="3" placeholder="例如：帮我制定本周高数复习计划" :disabled="busy" />
        <button type="submit" :disabled="busy || !goal.trim()">{{ busy ? '处理中…' : '开始' }}</button>
      </form>
      <p v-if="error" class="agent-error" role="alert">{{ error }}</p>
      <div v-if="selected" class="run-detail">
        <div class="run-title"><h2>{{ selected.goal }}</h2><span>{{ labels[selected.status] }}</span></div>
        <ol class="step-list"><li v-for="step in selected.steps" :key="step.number"><span class="step-index">{{ step.number }}</span><div><strong>{{ step.title }}</strong><small>{{ step.status }}</small><p v-if="step.detail">{{ step.detail }}</p></div></li></ol>
        <p v-if="selected.summary" class="run-summary">{{ selected.summary }}</p>
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
  </div>
</template>

<style scoped>
.agent-workspace{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:calc(100vh - 72px);max-width:1400px;margin:auto;color:#173b36}.run-rail{border-right:1px solid #d5e1d2;padding:32px 16px 32px 24px}.run-rail h2{font-size:.9rem;margin:0 0 24px}.muted{color:#59736a}.run-item{display:block;width:100%;text-align:left;border:0;background:transparent;padding:14px 12px;margin-bottom:5px;border-radius:12px;color:inherit;cursor:pointer}.run-item.active,.run-item:hover{background:#dfece2}.run-item span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}.run-item small{display:block;color:#526e64;margin-top:5px}.agent-main{padding:clamp(24px,5vw,64px);max-width:900px;width:100%}.agent-heading h1{font-family:Georgia,"Noto Serif SC",serif;font-size:clamp(2.5rem,5vw,4.5rem);font-weight:500;margin:0 0 12px}.agent-heading p{color:#4e695f;margin:0 0 32px}.agent-compose,.approval-panel{display:flex;flex-direction:column;gap:12px}.agent-compose label,.approval-panel label{font-weight:600;font-size:.9rem}textarea{width:100%;font:inherit;border:1px solid #a6bdb0;border-radius:12px;background:#f8faf5;color:#173b36;padding:14px;resize:vertical}button{font:inherit}button:focus-visible,textarea:focus-visible{outline:3px solid #b58853;outline-offset:2px}.agent-compose button,.approval-actions button{align-self:flex-start;border:0;border-radius:10px;background:#285d4e;color:#fff;padding:11px 24px;cursor:pointer}.agent-compose button:disabled,.approval-actions button:disabled{opacity:.55;cursor:wait}.agent-error{color:#9b392c;margin:16px 0}.run-detail{margin-top:52px}.run-title{display:flex;align-items:baseline;justify-content:space-between;gap:20px}.run-title h2{font-size:1.35rem;margin:0}.run-title span{color:#466c5a;font-size:.85rem;white-space:nowrap}.step-list{list-style:none;padding:0;margin:25px 0}.step-list li{display:flex;gap:15px;padding:16px 0;border-top:1px solid #d3e1d5}.step-index{font-variant-numeric:tabular-nums;color:#658476}.step-list strong{font-weight:600}.step-list small{margin-left:12px;color:#63786e}.step-list p{margin:8px 0 0;white-space:pre-wrap;line-height:1.6}.run-summary{padding:16px 0;white-space:pre-wrap;line-height:1.7}.approval-panel{padding:24px;background:#e1eddf;border-radius:14px}.approval-panel h3{margin:0}.approval-panel p{margin:0 0 6px;color:#466156}.approval-panel textarea{font-family:ui-monospace,monospace;font-size:.85rem}.approval-actions{display:flex;gap:10px;flex-wrap:wrap}.approval-actions .secondary{background:transparent;color:#285d4e;border:1px solid #7d9d8b}@media(max-width:700px){.agent-workspace{display:flex;flex-direction:column}.run-rail{border-right:0;border-bottom:1px solid #d5e1d2;padding:18px;max-height:200px;overflow:auto}.run-rail h2{margin-bottom:10px}.agent-main{padding:28px 18px}.run-detail{margin-top:36px}}
.chat-panel{margin-top:56px;border-top:1px solid #d3e1d5;padding-top:24px}.chat-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px}.chat-heading h2{font-size:1.25rem;margin:0}.chat-heading span{font-size:.8rem;color:#63786e}.chat-messages{display:grid;gap:10px;margin:18px 0;min-height:48px}.chat-message{display:grid;gap:4px;max-width:75%;margin:0;padding:10px 12px;border-radius:10px;line-height:1.55;white-space:pre-wrap}.chat-message.user{justify-self:end;background:#dfece2}.chat-message.assistant{background:#f0f4ed}.chat-message strong{font-size:.75rem;color:#527265}.chat-compose{display:flex;flex-direction:row;gap:8px}.chat-compose input{min-width:0;flex:1;border:1px solid #a6bdb0;border-radius:8px;padding:11px;font:inherit}.chat-compose button{border:0;border-radius:8px;background:#285d4e;color:#fff;padding:0 18px;cursor:pointer}.chat-compose button:disabled{opacity:.55}
</style>
