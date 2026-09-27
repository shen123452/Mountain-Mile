<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import VoxelIsland from './three/VoxelIsland.vue'
import RainOverlay from './RainOverlay.vue'
import type { TileData } from './three/terrain'
import type { IslandPalette } from './three/palettes'

const props = defineProps<{
  goal: string
  minutes: number
  tiles: TileData[]
  unlockedCount: number
  palette: IslandPalette
  busy: boolean
  error: string
}>()
const emit = defineEmits<{ finish: [minutes: number] }>()

const remaining = ref(props.minutes * 60)
const running = ref(true)
const selectedTile = ref<TileData | null>(null)
const timerCompleted = ref(false)
let deadline = Date.now() + remaining.value * 1000
let interval: number | undefined

const timeDisplay = computed(() => `${String(Math.floor(remaining.value / 60)).padStart(2, '0')}:${String(remaining.value % 60).padStart(2, '0')}`)
const elapsedMinutes = computed(() => Math.floor((props.minutes * 60 - remaining.value) / 60))

function updateTimer() {
  if (!running.value) return
  remaining.value = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
  if (remaining.value === 0 && !timerCompleted.value) {
    timerCompleted.value = true
    emit('finish', props.minutes)
  }
}

function toggleTimer() {
  if (timerCompleted.value) return
  if (running.value) {
    updateTimer()
    running.value = false
  } else {
    deadline = Date.now() + remaining.value * 1000
    running.value = true
    updateTimer()
  }
}

function endFocus() {
  if (props.busy) return
  timerCompleted.value = true
  emit('finish', elapsedMinutes.value)
}

function onVisibilityChange() {
  updateTimer()
}

onMounted(() => {
  document.body.classList.add('focus-mode')
  interval = window.setInterval(updateTimer, 250)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  document.body.classList.remove('focus-mode')
  if (interval) window.clearInterval(interval)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <section class="focus-room" aria-label="专注空间">
    <div class="focus-room__scene">
      <VoxelIsland :tiles="tiles" :unlocked-count="unlockedCount" :palette="palette" @select="selectedTile = $event" />
    </div>
    <RainOverlay />
    <header class="focus-room__heading">
      <p>山程 · 专注中</p>
      <h1>{{ goal }}</h1>
      <span v-if="selectedTile">已选地块 · {{ selectedTile.kind }} · 第 {{ selectedTile.unlockOrder }} 块</span>
      <span v-else>点击山屿上的地块查看详情</span>
    </header>
    <div class="focus-room__timer" role="timer" aria-live="off">
      <span>{{ timerCompleted ? '本次专注' : running ? '剩余时间' : '已暂停' }}</span>
      <strong>{{ timeDisplay }}</strong>
      <small>专注时长 {{ minutes }} 分钟</small>
    </div>
    <div class="focus-room__actions">
      <button v-if="!timerCompleted" class="focus-room__pause" type="button" @click="toggleTimer">{{ running ? '暂停计时' : '继续专注' }}</button>
      <button class="focus-room__finish" type="button" :disabled="busy" @click="endFocus">
        {{ busy ? '正在保存…' : timerCompleted ? '重试保存记录' : '结束并保存' }}
      </button>
      <p v-if="error" class="focus-room__error" role="alert">{{ error }}</p>
      <p v-else-if="timerCompleted" class="focus-room__message">计时结束，这段专注可以保存了。</p>
    </div>
  </section>
</template>

<style scoped>
.focus-room { position: fixed; inset: 0; z-index: 10; overflow: hidden; color: var(--ink); background: transparent; }
.focus-room__scene { position: absolute; inset: 0; background: radial-gradient(80% 55% at 68% 28%, rgba(143, 214, 176, 0.10) 0%, rgba(143, 214, 176, 0) 60%), linear-gradient(180deg, #0e2620 0%, #0a1d17 60%, #081712 100%); }
.focus-room__heading { position: absolute; top: clamp(1.5rem, 5vh, 3.5rem); left: clamp(1.5rem, 5vw, 5rem); z-index: 2; max-width: min(36rem, 60vw); }
.focus-room__heading p { margin: 0 0 0.45rem; color: var(--faint); font-size: 0.82rem; font-weight: 650; }
.focus-room__heading h1 { margin: 0; font-family: "Noto Serif SC", Georgia, serif; font-size: clamp(1.5rem, 2.8vw, 2.4rem); font-weight: 500; line-height: 1.2; overflow-wrap: anywhere; color: var(--ink); }
.focus-room__heading span { display: block; margin-top: 0.55rem; color: var(--muted); font-size: 0.85rem; }
.focus-room__timer { position: absolute; left: clamp(1.5rem, 5vw, 5rem); bottom: clamp(2rem, 7vh, 5rem); z-index: 2; display: flex; flex-direction: column; align-items: flex-start; gap: 0.35rem; font-variant-numeric: tabular-nums; }
.focus-room__timer span { color: var(--faint); font-size: 0.82rem; }
.focus-room__timer strong { color: var(--ink); font-size: clamp(3.5rem, 8vw, 6rem); font-weight: 400; line-height: 1; }
.focus-room__timer small { color: var(--faint); font-size: 0.78rem; }
.focus-room__actions { position: absolute; right: clamp(1.25rem, 4vw, 3.5rem); bottom: clamp(2rem, 7vh, 5rem); z-index: 2; display: grid; justify-items: end; gap: 0.6rem; }
.focus-room__finish { min-height: 2.8rem; padding: 0 1.1rem; border: 0; border-radius: 999px; color: #071712; background: var(--accent); font: inherit; font-size: 0.86rem; font-weight: 650; cursor: pointer; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4); }
.focus-room__pause { min-height: 2.4rem; padding: 0 0.9rem; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 999px; color: var(--ink); background: rgba(255, 255, 255, 0.06); font: inherit; font-size: 0.82rem; cursor: pointer; }
.focus-room__finish:hover { background: var(--accent-strong); }
.focus-room__finish:disabled { opacity: 0.65; cursor: wait; }
.focus-room__finish:focus-visible { outline: 3px solid var(--gold); outline-offset: 4px; }
.focus-room__error,.focus-room__message { max-width: 24rem; margin: 0; color: #e08a7d; font-size: 0.8rem; text-align: right; }
.focus-room__message { color: var(--muted); }
:global(body.focus-mode) { overflow: hidden; }
:global(body.focus-mode .topbar) { display: none; }
@media (max-width: 640px) {
  .focus-room__heading { top: 1.25rem; left: 1.25rem; max-width: calc(100vw - 2.5rem); }
  .focus-room__heading h1 { max-width: 90vw; font-size: 1.65rem; }
  .focus-room__heading span { font-size: 0.75rem; }
  .focus-room__timer { left: 1.25rem; bottom: 1.5rem; }
  .focus-room__timer strong { font-size: 3.6rem; }
  .focus-room__actions { right: 1.25rem; bottom: 1.5rem; }
  .focus-room__finish { min-height: 2.6rem; padding: 0 0.85rem; font-size: 0.78rem; }
  .focus-room__pause { min-height: 2.3rem; padding: 0 0.75rem; font-size: 0.75rem; }
}
@media (prefers-reduced-motion: reduce) { .focus-room * { scroll-behavior: auto !important; } }
</style>
