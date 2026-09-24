<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createIslandScene, type IslandScene } from './scene'
import type { TileData } from './terrain'
import type { IslandPalette } from './palettes'

const props = defineProps<{ tiles: TileData[]; unlockedCount: number; palette: IslandPalette }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let scene: IslandScene | null = null

function rebuild() {
  scene?.dispose()
  if (!canvas.value) return
  scene = createIslandScene(canvas.value, props.tiles, props.palette)
  scene.setUnlocked(props.unlockedCount)
}
onMounted(rebuild)
onBeforeUnmount(() => { scene?.dispose(); scene = null })
watch(() => props.tiles, rebuild)
watch(() => props.unlockedCount, count => scene?.setUnlocked(count))
watch(() => props.palette, palette => scene?.setPalette(palette))
</script>

<template><canvas ref="canvas" class="island-canvas" aria-label="可旋转的三维山屿预览" /></template>
<style scoped>.island-canvas{display:block;width:100%;height:100%;touch-action:none;outline:none}</style>
