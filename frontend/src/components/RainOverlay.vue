<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

type AmbientDetail = { playing?: boolean; volume?: number }
type Drop = {
  x: number
  y: number
  length: number
  speed: number
  sway: number
  phase: number
  opacity: number
  width: number
  depth: number
}

const canvas = ref<HTMLCanvasElement | null>(null)
let frame = 0
let resizeObserver: ResizeObserver | undefined
let mediaQuery: MediaQueryList | undefined
let reducedMotion = false
let drops: Drop[] = []
let width = 1
let height = 1
let pixelRatio = 1
let lastTime = 0
let targetIntensity = 0.02
let intensity = 0.02
let seed = 918273

function random() {
  seed = (seed * 1664525 + 1013904223) >>> 0
  return seed / 4294967296
}

function currentAmbient(): AmbientDetail {
  const playing = document.documentElement.dataset.ambient === 'on'
  const volume = Number.parseFloat(document.documentElement.dataset.ambientVolume ?? '0.3')
  return { playing, volume: Number.isFinite(volume) ? volume : 0.3 }
}

function setAmbient(detail: AmbientDetail) {
  const volume = Math.min(1, Math.max(0, detail.volume ?? 0.3))
  // 播放雨声时随音量增强；未播放时保留一层隐约雨丝，避免整屏"干"掉
  targetIntensity = detail.playing ? 0.22 + volume * 0.78 : 0.06
}

function makeDrop(initial = false): Drop {
  const depth = random()
  return {
    x: random() * width,
    y: initial ? random() * height : -random() * height * 0.18 - 10,
    length: 8 + depth * 24,
    speed: 250 + depth * 270,
    sway: 3 + random() * 13,
    phase: random() * Math.PI * 2,
    opacity: 0.08 + depth * 0.2,
    width: 0.45 + depth * 0.8,
    depth,
  }
}

function rebuildDrops() {
  const count = reducedMotion ? 0 : Math.round(Math.min(260, Math.max(100, width * 0.18)))
  drops = Array.from({ length: count }, () => makeDrop(true))
}

function resize() {
  const element = canvas.value
  if (!element) return
  const bounds = element.getBoundingClientRect()
  width = Math.max(1, bounds.width)
  height = Math.max(1, bounds.height)
  pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5)
  element.width = Math.round(width * pixelRatio)
  element.height = Math.round(height * pixelRatio)
  rebuildDrops()
}

function draw(now: number) {
  const element = canvas.value
  const context = element?.getContext('2d')
  if (!element || !context) return
  const delta = Math.min(0.04, Math.max(0.001, (now - lastTime) / 1000 || 0.016))
  lastTime = now
  intensity += (targetIntensity - intensity) * Math.min(1, delta * 2.6)
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  context.clearRect(0, 0, width, height)

  if (intensity > 0.01) {
    const wind = Math.sin(now * 0.00018) * 0.7 + Math.sin(now * 0.000067 + 2) * 0.45
    for (const drop of drops) {
      drop.y += drop.speed * delta
      const drift = wind * drop.sway + Math.sin(now * 0.001 + drop.phase) * 1.8
      const x = drop.x + drift
      const y = drop.y
      if (y - drop.length > height + 14) Object.assign(drop, makeDrop())
      // 由远及近的墨绿→墨黑渐层：远景偏冷、近景更深，在浅底上以深色细线呈现
      const t = drop.depth
      const r = Math.round(112 - 89 * t)
      const g = Math.round(140 - 81 * t)
      const b = Math.round(130 - 76 * t)
      const alpha = Math.min(0.55, (0.06 + t * 0.46) * intensity)
      const gradient = context.createLinearGradient(x, y - drop.length, x + 1.5, y)
      gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`)
      gradient.addColorStop(0.45, `rgba(${r}, ${g}, ${b}, ${alpha * 0.45})`)
      gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, ${alpha})`)
      context.beginPath()
      context.moveTo(x, y - drop.length)
      context.lineTo(x + 1.5, y)
      context.strokeStyle = gradient
      context.lineWidth = drop.width
      context.lineCap = 'round'
      context.stroke()
    }
  }

  frame = requestAnimationFrame(draw)
}

function onAmbientChange(event: Event) {
  const custom = event as CustomEvent<AmbientDetail>
  setAmbient(custom.detail ?? {})
}

function onMotionChange(event: MediaQueryListEvent) {
  reducedMotion = event.matches
  resize()
}

onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion = mediaQuery.matches
  mediaQuery.addEventListener('change', onMotionChange)
  setAmbient(currentAmbient())
  window.addEventListener('mountain-mile:ambient-change', onAmbientChange)
  resizeObserver = new ResizeObserver(resize)
  if (canvas.value) resizeObserver.observe(canvas.value)
  resize()
  frame = requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  resizeObserver?.disconnect()
  mediaQuery?.removeEventListener('change', onMotionChange)
  window.removeEventListener('mountain-mile:ambient-change', onAmbientChange)
})
</script>

<template>
  <canvas ref="canvas" class="rain-overlay" aria-hidden="true" />
</template>

<style scoped>
.rain-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 1;
}
</style>
