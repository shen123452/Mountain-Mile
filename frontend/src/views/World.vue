<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VoxelIsland from '../components/three/VoxelIsland.vue'
import { palettes, type PaletteName } from '../components/three/palettes'
import { generateTerrain } from '../components/three/terrain'
import { useGoalStore } from '../stores/goals'

const store = useGoalStore()
const selectedId = ref<string | null>(null)
const showForm = ref(false)
const editing = ref(false)
const pending = ref(false)
const error = ref('')
const name = ref('')
const description = ref('')
const palette = ref<PaletteName>('jade')
const weeklyTarget = ref<number | null>(null)
const focusId = ref<string | null>(null)
const focusMinutes = ref(25)
const focusBusy = ref(false)
const selected = computed(() => store.goals.find(goal => goal.id === selectedId.value) ?? store.goals[0] ?? null)
const tiles = computed(() => selected.value ? generateTerrain({ seed: selected.value.seed }) : [])

onMounted(async () => {
  try { await store.load(); selectedId.value = store.goals[0]?.id ?? null }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '目标加载失败' }
})

function openCreate() {
  editing.value = false; showForm.value = true; error.value = ''
  name.value = ''; description.value = ''; palette.value = 'jade'; weeklyTarget.value = null
}
function openEdit() {
  if (!selected.value) return
  editing.value = true; showForm.value = true; error.value = ''
  name.value = selected.value.name; description.value = selected.value.description ?? ''
  palette.value = selected.value.palette_variant; weeklyTarget.value = selected.value.weekly_target_minutes
}
async function save() {
  if (pending.value || !name.value.trim()) return
  pending.value = true; error.value = ''
  try {
    const targetMinutes = Number(weeklyTarget.value)
    const draft = { name: name.value.trim(), description: description.value.trim(), palette_variant: palette.value, weekly_target_minutes: targetMinutes > 0 ? targetMinutes : null }
    const goal = editing.value && selected.value ? await store.update(selected.value.id, draft) : await store.create(draft)
    selectedId.value = goal.id
    showForm.value = false
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '保存失败' }
  finally { pending.value = false }
}
async function archive() {
  if (!selected.value || !window.confirm(`归档「${selected.value.name}」？`)) return
  try { await store.archive(selected.value.id); selectedId.value = store.goals[0]?.id ?? null }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '归档失败' }
}
async function startFocus() {
  if (!selected.value || focusBusy.value) return
  focusBusy.value = true
  try { const r = await fetch('/api/focus-sessions', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ goal_id: selected.value.id, planned_minutes: focusMinutes.value }) }); const b = await r.json(); if (!r.ok) throw new Error(b.error?.message ?? '无法开始专注'); focusId.value = b.data.id } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法开始专注' } finally { focusBusy.value = false }
}
async function finishFocus() {
  if (!focusId.value || focusBusy.value) return
  focusBusy.value = true
  try { const r = await fetch(`/api/focus-sessions/${focusId.value}`, { method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actual_minutes: focusMinutes.value }) }); const b = await r.json(); if (!r.ok) throw new Error(b.error?.message ?? '无法完成专注'); focusId.value = null; await store.load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法完成专注' } finally { focusBusy.value = false }
}
</script>

<template>
  <section class="world-page">
    <aside class="goal-rail">
      <div class="rail-head"><div><h1>我的群岛</h1><p>每个目标，都有自己的山形。</p></div><button class="add-button" type="button" @click="openCreate">新建目标</button></div>
      <p v-if="store.loading" class="rail-message">正在加载目标…</p>
      <p v-else-if="!store.goals.length" class="rail-message">还没有山屿。新建第一个目标，看看它如何从云海中升起。</p>
      <ul v-else class="goal-list"><li v-for="goal in store.goals" :key="goal.id"><button type="button" :class="{ active: selected?.id === goal.id }" @click="selectedId = goal.id"><span class="goal-mark" :style="{ background: palettes[goal.palette_variant].top }"></span><span><strong>{{ goal.name }}</strong><small>已解锁 {{ goal.unlocked_count }} 块地形</small></span></button></li></ul>
      <p v-if="error && !showForm" class="world-error" role="alert">{{ error }}</p>
      <RouterLink class="demo-link" to="/terrain-demo">打开地形演示</RouterLink>
    </aside>
    <div class="world-main">
      <div v-if="selected" class="selected-head"><div><p>目标山屿</p><h2>{{ selected.name }}</h2><span>{{ selected.description || '开始投入时间，这座山会记录你的每一步。' }}</span></div><div class="selected-actions"><button type="button" @click="openEdit">编辑</button><button type="button" @click="archive">归档</button></div></div>
      <div v-if="selected" class="focus-bar"><strong>{{ focusId ? '专注进行中' : '为这座山投入时间' }}</strong><label><input v-model.number="focusMinutes" type="number" min="1" max="240" :disabled="!!focusId" /> 分钟</label><button v-if="!focusId" type="button" :disabled="focusBusy" @click="startFocus">开始专注</button><button v-else type="button" :disabled="focusBusy" @click="finishFocus">完成专注</button></div>
      <div class="island-stage" :style="{ backgroundColor: selected ? palettes[selected.palette_variant].sky : '#e8eee4' }"><VoxelIsland v-if="selected" :key="selected.id" :tiles="tiles" :unlocked-count="selected.unlocked_count" :palette="palettes[selected.palette_variant]" /><p v-else class="empty-stage">你的第一座山屿即将出现在这里。</p></div>
      <p v-if="selected" class="stage-caption">目标 ID 决定山形；学习记录与地块生长将在 M5 接入。</p>
    </div>
    <div v-if="showForm" class="form-backdrop" @click.self="showForm = false"><form class="goal-form" @submit.prevent="save"><h2>{{ editing ? '编辑目标' : '新建目标' }}</h2><label for="goal-name">目标名称</label><input id="goal-name" v-model="name" required maxlength="120" autofocus /><label for="goal-description">描述（选填）</label><textarea id="goal-description" v-model="description" maxlength="2000" rows="3"></textarea><label for="goal-palette">山色</label><select id="goal-palette" v-model="palette"><option value="jade">青绿</option><option value="azurite">石青</option><option value="ochre">赭石</option><option value="pale">浅绢</option></select><label for="goal-target">每周目标分钟（选填）</label><input id="goal-target" v-model.number="weeklyTarget" type="number" min="1" max="10080" /><p v-if="error" class="world-error" role="alert">{{ error }}</p><div class="form-actions"><button type="button" @click="showForm = false">取消</button><button type="submit" :disabled="pending">{{ pending ? '保存中…' : '保存目标' }}</button></div></form></div>
  </section>
</template>

<style scoped>
.world-page{display:grid;grid-template-columns:minmax(270px,340px) 1fr;min-height:calc(100vh - 72px);background:#f4f7ef;color:#173b36}.goal-rail{padding:2.5rem 1.5rem;border-right:1px solid #d8e2d6;background:#f8faf4}.rail-head h1,.selected-head h2,.goal-form h2{font-family:"Noto Serif SC",Georgia,serif;font-weight:500}.rail-head h1{font-size:2rem;margin:0}.rail-head p{color:#5a7469;margin:.4rem 0 1.5rem}.add-button,.form-actions button:last-child{border:0;border-radius:8px;padding:.7rem 1rem;background:#1e5b4c;color:#fff;font:inherit;font-weight:650;cursor:pointer}.goal-list{list-style:none;padding:0;margin:2rem 0}.goal-list li+li{margin-top:.4rem}.goal-list button{display:flex;align-items:center;gap:.8rem;width:100%;padding:.85rem;text-align:left;border:1px solid transparent;border-radius:10px;background:transparent;color:inherit;cursor:pointer}.goal-list button.active,.goal-list button:hover{background:#e8f0e8;border-color:#c9dbc9}.goal-mark{width:34px;height:34px;border-radius:7px;transform:rotate(-18deg);flex:none}.goal-list strong,.goal-list small{display:block}.goal-list small{font-size:.75rem;color:#577369;margin-top:.2rem}.rail-message{line-height:1.7;color:#597368}.demo-link{display:inline-block;margin-top:1.5rem;color:#2f6957;text-underline-offset:3px;font-size:.85rem}.world-main{min-width:0;display:flex;flex-direction:column}.selected-head{display:flex;justify-content:space-between;gap:1rem;padding:2.5rem 3vw 1.5rem}.selected-head p{font-size:.8rem;color:#57816d;margin:0 0 .4rem}.selected-head h2{font-size:clamp(1.8rem,3vw,2.8rem);margin:0 0 .5rem}.selected-head span{color:#5a7469}.selected-actions{display:flex;gap:.5rem;align-self:start}.selected-actions button,.form-actions button:first-child{padding:.5rem .8rem;border:1px solid #9bb8a8;border-radius:8px;background:#fff;color:#255849;cursor:pointer}.island-stage{flex:1;min-height:430px;position:relative}.empty-stage{position:absolute;inset:0;display:grid;place-items:center;color:#537264}.stage-caption{padding:1rem 3vw;margin:0;color:#668073;font-size:.8rem}.form-backdrop{position:fixed;inset:0;z-index:5;background:#173b3688;display:grid;place-items:center;padding:1rem}.goal-form{display:flex;flex-direction:column;width:min(100%,480px);max-height:95vh;overflow:auto;padding:2rem;background:#f8faf4;border-radius:12px;box-shadow:0 18px 50px #123a2a38}.goal-form h2{margin:0 0 1rem;font-size:1.8rem}.goal-form label{margin:1rem 0 .4rem;font-weight:650}.goal-form input,.goal-form textarea,.goal-form select{padding:.7rem;border:1px solid #9bb8a8;border-radius:7px;background:#fff;color:#173b36;font:inherit}.form-actions{display:flex;justify-content:flex-end;gap:.5rem;margin-top:1.5rem}.world-error{color:#9b342d;font-size:.9rem}.world-page button:focus-visible,.world-page input:focus-visible,.world-page select:focus-visible,.world-page textarea:focus-visible{outline:3px solid #b58853;outline-offset:2px}@media(max-width:800px){.world-page{grid-template-columns:1fr}.goal-rail{border-right:0;border-bottom:1px solid #d8e2d6;padding:1.5rem 5vw}.goal-list{display:flex;overflow:auto;gap:.5rem;margin:1rem 0}.goal-list li{min-width:175px}.goal-list li+li{margin:0}.selected-head{padding:1.5rem 5vw}.island-stage{min-height:400px}}@media(max-width:480px){.selected-head{display:block}.selected-actions{margin-top:1rem}.island-stage{min-height:350px}}
.focus-bar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:0 3vw 18px;color:#315d4e}.focus-bar label{margin:0;display:flex;align-items:center;gap:6px}.focus-bar input{width:70px;padding:6px;border:1px solid #9bb8a8;border-radius:6px}.focus-bar button{padding:7px 12px;border:0;border-radius:7px;background:#285d4e;color:#fff;cursor:pointer}.focus-bar button:disabled{opacity:.55}
</style>
