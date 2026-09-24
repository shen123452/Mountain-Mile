<script setup lang="ts">
import { computed, ref } from 'vue'
import VoxelIsland from '../components/three/VoxelIsland.vue'
import { generateTerrain, unlockedTileCount } from '../components/three/terrain'
import { palettes, type PaletteName } from '../components/three/palettes'

const seed = ref('mountain-mile-demo')
const paletteName = ref<PaletteName>('jade')
const unlocked = ref(20)
const tiles = computed(() => generateTerrain({ seed: seed.value }))
const visible = computed(() => unlockedTileCount(tiles.value.length, 0, unlocked.value))
const kindNames = { forest: '林地', moss: '苔地', water: '水面', rock: '岩地', river: '河道', village: '村落', waterfall: '瀑布' }
const summary = computed(() => Object.entries(kindNames).map(([kind, name]) => {
  const count = tiles.value.filter(tile => tile.kind === kind && tile.unlockOrder <= visible.value).length
  return count ? `${name} ${count}` : ''
}).filter(Boolean).join('、'))
</script>

<template>
  <section class="world-demo">
    <div class="world-copy"><h1>一座山，从每一步开始。</h1><p>相同的目标种子始终生成相同的山形。拖动山屿可旋转视角；调整地块数，预览学习投入如何让地形逐步显现。</p>
      <div class="world-controls"><label for="seed">目标种子</label><input id="seed" v-model="seed" maxlength="60" />
        <label for="palette">山色</label><select id="palette" v-model="paletteName"><option value="jade">青绿</option><option value="azurite">石青</option><option value="ochre">赭石</option><option value="pale">浅绢</option></select>
        <label for="unlocked">解锁地块 <strong>{{ visible }} / {{ tiles.length }}</strong></label><input id="unlocked" v-model.number="unlocked" type="range" min="0" :max="tiles.length" />
      </div><p class="world-note">M2 地形演示。此处使用预览数据；目标和真实学习记录将在后续里程碑接入。</p>
    </div>
    <div class="world-stage" :style="{ backgroundColor: palettes[paletteName].sky }"><VoxelIsland :tiles="tiles" :unlocked-count="visible" :palette="palettes[paletteName]" /><p class="world-summary">{{ summary || '尚未解锁地块' }}</p></div>
  </section>
</template>

<style scoped>
.world-demo{display:grid;grid-template-columns:minmax(300px,38%) 1fr;min-height:calc(100vh - 72px);color:#173b36}.world-copy{padding:clamp(2rem,5vw,5rem);align-self:center}.world-copy h1{font-family:"Noto Serif SC",Georgia,serif;font-size:clamp(2.2rem,4vw,4rem);font-weight:500;line-height:1.2;margin:0 0 1.5rem}.world-copy>p{line-height:1.75;color:#466158;max-width:34rem}.world-controls{display:grid;gap:.5rem;margin-top:2.5rem;max-width:28rem}.world-controls label{font-weight:650;margin-top:.8rem}.world-controls label strong{float:right;font-variant-numeric:tabular-nums}.world-controls input:not([type=range]),.world-controls select{padding:.7rem;border:1px solid #a8bcae;border-radius:8px;background:#fff;color:#173b36;font:inherit}.world-controls input:focus-visible,.world-controls select:focus-visible{outline:3px solid #b58853;outline-offset:2px}.world-controls input[type=range]{accent-color:#23644f}.world-note{font-size:.85rem}.world-stage{position:relative;min-height:560px}.world-summary{position:absolute;bottom:1rem;left:1rem;right:1rem;margin:0;padding:.7rem 1rem;background:#f7f8f1e8;font-size:.82rem;line-height:1.5;color:#315a4d}@media(max-width:850px){.world-demo{grid-template-columns:1fr}.world-copy{padding:2.5rem 6vw}.world-stage{min-height:480px}}@media(max-width:480px){.world-stage{min-height:360px}}
</style>
