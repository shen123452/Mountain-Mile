<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { nextTick, onMounted, ref } from 'vue'

interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; pending?: boolean; failed?: boolean }

const messages = ref<ChatMessage[]>([])
const input = ref('')
const busy = ref(false)
const conversationId = ref<string | null>(null)
const error = ref('')
const scrollRef = ref<HTMLElement | null>(null)

function renderMd(text: string) {
  return DOMPurify.sanitize(marked.parse(text, { async: false, breaks: true }) as string)
}
function scrollBottom() {
  void nextTick(() => scrollRef.value?.scrollTo({ top: scrollRef.value.scrollHeight, behavior: 'smooth' }))
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
  messages.value = detail.data.messages
  scrollBottom()
}

async function send() {
  if (!conversationId.value || !input.value.trim() || busy.value) return
  const content = input.value.trim(); input.value = ''; busy.value = true
  const pendingId = `assistant-pending-${Date.now()}`
  messages.value.push({ id: `user-${Date.now()}`, role: 'user', content }, { id: pendingId, role: 'assistant', content: '正在思考…', pending: true })
  scrollBottom()
  try {
    const response = await fetch(`/api/conversations/${conversationId.value}/messages`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content }) })
    const body = await response.json(); if (!response.ok) throw new Error(body.error?.message ?? body.detail ?? '发送失败')
    const reply = body.data.message
    const index = messages.value.findIndex(item => item.id === pendingId)
    if (index >= 0) messages.value[index] = { id: reply.id, role: reply.role, content: reply.content }
  } catch (cause) {
    const index = messages.value.findIndex(item => item.id === pendingId)
    const fallback = cause instanceof Error ? cause.message : '发送失败'
    if (index >= 0) messages.value[index] = { id: pendingId, role: 'assistant', content: `发送失败：${fallback}`, failed: true }
  } finally { busy.value = false; scrollBottom() }
}

onMounted(() => { void loadConversation() })
</script>

<template>
  <section class="chat-page">
    <header class="chat-page-head">
      <div><h1>学习对话</h1><p>纯问答 · 自动检索你的资料库回答 · 不执行任何操作</p></div>
      <span class="chat-note">消息永久保存在你的账户</span>
    </header>
    <div ref="scrollRef" class="chat-flow">
      <p v-if="!messages.length" class="chat-empty">从一个学习问题开始——比如「什么是 JVM 内存模型？」或「我上传的资料里讲了什么？」。<br>想让向导<strong>执行操作</strong>（建计划、拆任务），去「向导」页。</p>
      <div v-for="message in messages" :key="message.id" :class="['chat-row', message.role]">
        <span class="chat-avatar" :class="message.role">{{ message.role === 'user' ? '你' : 'MM' }}</span>
        <div class="chat-bubble">
          <strong>{{ message.role === 'user' ? '你' : '向导' }}</strong>
          <div v-if="message.role === 'assistant' && !message.pending && !message.failed" class="reply-body" v-html="renderMd(message.content)"></div>
          <span v-else class="plain-text">{{ message.content }}</span>
        </div>
      </div>
    </div>
    <form class="chat-dock" @submit.prevent="send">
      <input v-model="input" maxlength="10000" placeholder="问问你的学习向导…" :disabled="busy" />
      <button type="submit" :disabled="busy || !input.trim()">{{ busy ? '思考中…' : '发送' }}</button>
    </form>
    <p v-if="error" class="chat-page-error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.chat-page{display:flex;flex-direction:column;height:calc(100vh - 72px);max-width:860px;margin:0 auto;padding:0 clamp(1.25rem,4vw,3rem);color:#173b36}
.chat-page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;padding:26px 0 16px;border-bottom:1px solid #d6e1d5}
.chat-page-head h1{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:1.7rem}
.chat-page-head p{margin:.4rem 0 0;color:#5f756d;font-size:.76rem}
.chat-note{color:#7c9688;font-size:.7rem;flex-shrink:0}
.chat-flow{flex:1;min-height:0;overflow-y:auto;display:grid;gap:14px;align-content:start;padding:22px 4px}
.chat-empty{margin:2rem 0;color:#678075;font-size:.86rem;line-height:1.9}
.chat-empty strong{color:#285d4e}
.chat-row{display:flex;gap:10px;align-items:flex-start}
.chat-row.user{flex-direction:row-reverse}
.chat-avatar{flex-shrink:0;display:grid;place-items:center;width:34px;height:34px;border-radius:9px;font-size:.68rem;font-weight:750}
.chat-avatar.assistant{background:#285d4e;color:#f3f7e9}
.chat-avatar.user{background:#e1eee2;color:#2f6b58}
.chat-bubble{max-width:min(78%,620px);padding:11px 14px;border:1px solid #d8e4d8;border-radius:10px;background:#fbfcf8;display:grid;gap:6px}
.chat-row.user .chat-bubble{background:#e9f2ea;border-color:#cfe0d2}
.chat-bubble strong{font-size:.7rem;color:#527265}
.plain-text{white-space:pre-wrap;font-size:.84rem}
.chat-row.user .plain-text{font-size:.86rem}
.chat-row.assistant .chat-bubble.failed{border-color:#e0c4bc;background:#fbf3f0}
.chat-row.assistant .chat-bubble.failed .plain-text{color:#8c4638;font-size:.78rem}
.chat-row.assistant .chat-bubble.pending .plain-text{color:#527265;animation:thinking 1.2s ease-in-out infinite}
@keyframes thinking{0%,100%{opacity:.45}50%{opacity:1}}
.chat-dock{display:flex;gap:8px;padding:14px 0 18px;border-top:1px solid #d6e1d5}
.chat-dock input{min-width:0;flex:1;height:46px;border:1px solid #a6bdb0;border-radius:9px;padding:0 14px;font:inherit;background:#fbfcf8;color:#173b36}
.chat-dock button{border:0;border-radius:9px;background:#285d4e;color:#fff;padding:0 22px;cursor:pointer;font:inherit;font-weight:650}
.chat-dock button:disabled{opacity:.55}
.chat-page-error{margin:0 0 10px;color:#8c4638;font-size:.78rem}
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
@media(max-width:640px){.chat-bubble{max-width:88%}.chat-page-head h1{font-size:1.4rem}}
</style>
