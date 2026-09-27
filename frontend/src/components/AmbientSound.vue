<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const AUDIO_SRC = '/mountain-rain.mp3'
const VOLUME_KEY = 'mountain-mile:ambient-volume'

const expanded = ref(false)
const playing = ref(false)
const volume = ref(0.3)
const audio = ref<HTMLAudioElement | null>(null)
const control = ref<HTMLElement | null>(null)
const wasPlaying = ref(false)

const volumePercent = computed(() => Math.round(volume.value * 100))
const volumeLabel = computed(() => (volume.value === 0 ? '静音' : `音量 ${volumePercent.value}%`))

function announceAmbientState() {
  const isPlaying = Boolean(audio.value && !audio.value.paused)
  document.documentElement.dataset.ambient = isPlaying ? 'on' : 'off'
  document.documentElement.dataset.ambientVolume = String(volume.value)
  window.dispatchEvent(new CustomEvent('mountain-mile:ambient-change', { detail: { playing: isPlaying, volume: volume.value } }))
}

function readVolume() {
  const saved = Number.parseFloat(localStorage.getItem(VOLUME_KEY) ?? '')
  if (Number.isFinite(saved)) volume.value = Math.min(1, Math.max(0, saved))
}

function syncVolume(value: number) {
  volume.value = Math.min(1, Math.max(0, value))
  if (audio.value) audio.value.volume = volume.value
  localStorage.setItem(VOLUME_KEY, String(volume.value))
  announceAmbientState()
}

async function togglePlayback() {
  if (!audio.value) return
  if (audio.value.paused) {
    try {
      await audio.value.play()
      playing.value = true
      announceAmbientState()
    } catch {
      playing.value = false
      announceAmbientState()
    }
  } else {
    audio.value.pause()
    playing.value = false
    announceAmbientState()
  }
  expanded.value = true
}

function closeOnOutside(event: MouseEvent) {
  const target = event.target as Node | null
  if (target && !control.value?.contains(target)) expanded.value = false
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') expanded.value = false
}

function onVisibilityChange() {
  if (!audio.value) return
  if (document.hidden) {
    wasPlaying.value = !audio.value.paused
    if (wasPlaying.value) audio.value.pause()
  } else if (wasPlaying.value) {
    wasPlaying.value = false
    void audio.value.play().then(() => { playing.value = true }).catch(() => { playing.value = false })
  }
}

watch(volume, (value) => {
  if (audio.value) audio.value.volume = value
})

onMounted(() => {
  readVolume()
  const element = new Audio(AUDIO_SRC)
  element.loop = true
  element.preload = 'none'
  element.volume = volume.value
  element.addEventListener('play', () => { playing.value = true; announceAmbientState() })
  element.addEventListener('pause', () => { playing.value = false; announceAmbientState() })
  audio.value = element
  announceAmbientState()
  document.addEventListener('mousedown', closeOnOutside)
  document.addEventListener('keydown', closeOnEscape)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', closeOnOutside)
  document.removeEventListener('keydown', closeOnEscape)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  audio.value?.pause()
  if (audio.value) audio.value.src = ''
  delete document.documentElement.dataset.ambient
  delete document.documentElement.dataset.ambientVolume
})
</script>

<template>
  <div ref="control" class="ambient-sound" :class="{ 'ambient-sound--expanded': expanded }">
    <div id="ambient-volume" v-show="expanded" class="ambient-sound__panel" aria-label="环境音量">
      <div class="ambient-sound__track">
        <div class="ambient-sound__fill" :style="{ height: `${volumePercent}%` }" />
        <input
          v-model.number="volume"
          class="ambient-sound__range"
          type="range"
          min="0"
          max="1"
          step="0.01"
          :aria-label="volumeLabel"
          :aria-valuetext="volumeLabel"
          @input="syncVolume(volume)"
        >
      </div>
      <span class="ambient-sound__value">{{ volumePercent }}</span>
    </div>
    <button
      class="ambient-sound__button"
      type="button"
      :aria-label="playing ? '暂停山间雨声' : '播放山间雨声'"
      :aria-expanded="expanded"
      aria-controls="ambient-volume"
      @click="togglePlayback"
    >
      <svg v-if="playing" viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 4.5A1.5 1.5 0 0 1 8 6v12a1.5 1.5 0 0 1-3 0V6a1.5 1.5 0 0 1 1.5-1.5Zm11 0A1.5 1.5 0 0 1 19 6v12a1.5 1.5 0 0 1-3 0V6a1.5 1.5 0 0 1 1.5-1.5Z" /></svg>
      <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.2v5.6h3.2l4.3 3.4V5.8L7.2 9.2H4Zm12.2-.8a1 1 0 0 0-1.4 1.4 4.5 4.5 0 0 1 0 6.4 1 1 0 0 0 1.4 1.4 6.5 6.5 0 0 0 0-9.2ZM18.6 5a1 1 0 0 0-1.4 1.4 7.9 7.9 0 0 1 0 11.2 1 1 0 0 0 1.4 1.4 9.9 9.9 0 0 0 0-14Z" /></svg>
      <span class="ambient-sound__pulse" :class="{ 'ambient-sound__pulse--active': playing }" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.ambient-sound {
  position: fixed;
  right: clamp(1rem, 3vw, 2.5rem);
  bottom: clamp(1rem, 3vw, 2.25rem);
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  color: var(--ink);
  font-family: inherit;
}

.ambient-sound__panel {
  width: 4.5rem;
  padding: 0.8rem 0.65rem 0.7rem;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 1.5rem;
  background: rgba(8, 23, 18, 0.88);
  box-shadow: 0 14px 35px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(14px);
  animation: sound-panel-in 180ms ease-out;
  text-align: center;
}

.ambient-sound__track {
  position: relative;
  width: 1rem;
  height: 6.5rem;
  margin: 0 auto 0.4rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.ambient-sound__track:has(.ambient-sound__range:focus-visible) { outline: 3px solid var(--gold); outline-offset: 4px; }

.ambient-sound__fill {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  border-radius: inherit;
  background: var(--accent);
}

.ambient-sound__range {
  position: absolute;
  inset: 0;
  width: 6.5rem;
  height: 1rem;
  margin: 2.75rem -2.75rem;
  cursor: ns-resize;
  opacity: 0;
  transform: rotate(-90deg);
}

.ambient-sound__value {
  color: var(--faint);
  font-size: 0.68rem;
  font-variant-numeric: tabular-nums;
}

.ambient-sound__button {
  position: relative;
  display: grid;
  width: 3rem;
  height: 3rem;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  color: var(--ink);
  background: rgba(8, 23, 18, 0.88);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.35);
  cursor: pointer;
  transition: transform 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.ambient-sound__button:hover { background: rgba(255, 255, 255, 0.1); transform: translateY(-2px); box-shadow: 0 14px 30px rgba(0, 0, 0, 0.45); }
.ambient-sound__button:focus-visible { outline: 3px solid var(--gold); outline-offset: 4px; }
.ambient-sound__button svg { width: 1.15rem; height: 1.15rem; fill: currentColor; }
.ambient-sound__pulse { position: absolute; inset: -0.35rem; border: 1px solid rgba(143, 214, 176, 0.38); border-radius: inherit; opacity: 0; }
.ambient-sound__pulse--active { animation: sound-pulse 2.3s ease-out infinite; }

@keyframes sound-panel-in { from { opacity: 0; transform: translateY(0.35rem) scale(0.96); } to { opacity: 1; transform: none; } }
@keyframes sound-pulse { 0% { opacity: 0.65; transform: scale(0.92); } 100% { opacity: 0; transform: scale(1.25); } }
@media (prefers-reduced-motion: reduce) { .ambient-sound__panel, .ambient-sound__pulse--active { animation: none; } .ambient-sound__button { transition: none; } }
@media (max-width: 520px) { .ambient-sound { right: 1rem; bottom: 1rem; } .ambient-sound__button { width: 2.75rem; height: 2.75rem; } }
</style>
