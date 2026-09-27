<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VoxelIsland from '../components/three/VoxelIsland.vue'
import FocusRoom from '../components/FocusRoom.vue'
import { palettes, type PaletteName } from '../components/three/palettes'
import { generateTerrain, type TileData } from '../components/three/terrain'
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
const selectedTile = ref<TileData | null>(null)
const focusError = ref('')
const selected = computed(() => store.goals.find(goal => goal.id === selectedId.value) ?? store.goals[0] ?? null)
const tiles = computed(() => selected.value ? generateTerrain({ seed: selected.value.seed }) : [])
const totalTileCount = computed(() => tiles.value.length)
const progressPercent = (count: number) => totalTileCount.value ? Math.round(count / totalTileCount.value * 100) : 0
const tileLabels: Record<TileData['kind'], string> = { forest: '森林', moss: '苔地', water: '水域', rock: '岩地', river: '河道', village: '村落', waterfall: '瀑布' }

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
  try { const r = await fetch('/api/focus-sessions', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ goal_id: selected.value.id, planned_minutes: focusMinutes.value }) }); const b = await r.json(); if (!r.ok) throw new Error(b.error?.message ?? '无法开始专注'); focusId.value = b.data.id; focusError.value = '' } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法开始专注' } finally { focusBusy.value = false }
}
async function finishFocus(actualMinutes: number) {
  if (!focusId.value || focusBusy.value) return
  focusBusy.value = true
  try { const r = await fetch(`/api/focus-sessions/${focusId.value}`, { method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actual_minutes: actualMinutes }) }); const b = await r.json(); if (!r.ok) throw new Error(b.error?.message ?? '无法完成专注'); focusId.value = null; focusError.value = ''; await store.load() } catch (cause) { focusError.value = cause instanceof Error ? cause.message : '无法完成专注' } finally { focusBusy.value = false }
}
</script>

<template>
  <FocusRoom v-if="focusId && selected" :key="focusId" :goal="selected.name" :minutes="focusMinutes" :tiles="tiles" :unlocked-count="selected.unlocked_count" :palette="palettes[selected.palette_variant]" :busy="focusBusy" :error="focusError" @finish="finishFocus" />
  <section v-else class="world-page">
    <aside class="goal-rail">
      <div class="rail-head"><div><h1>我的群岛</h1><p>学习目标</p></div><button class="add-button" type="button" aria-label="新建目标" title="新建目标" @click="openCreate"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg></button></div>
      <p v-if="store.loading" class="rail-message">正在加载目标…</p>
      <p v-else-if="!store.goals.length" class="rail-message">还没有山屿。新建第一个目标，看看它如何从云海中升起。</p>
      <ul v-else class="goal-list"><li v-for="goal in store.goals" :key="goal.id"><button type="button" :class="{ active: selected?.id === goal.id }" :aria-pressed="selected?.id === goal.id" @click="selectedId = goal.id"><span class="goal-mark" :style="{ '--goal-color': palettes[goal.palette_variant].top }"></span><span class="goal-copy"><strong>{{ goal.name }}</strong><small>{{ goal.unlocked_count }} / {{ totalTileCount }} 地块</small><span class="goal-progress" aria-hidden="true"><i :style="{ width: `${progressPercent(goal.unlocked_count)}%` }"></i></span></span></button></li></ul>
      <p v-if="error && !showForm" class="world-error" role="alert">{{ error }}</p>
      <RouterLink class="demo-link" to="/terrain-demo">地形演示 <span aria-hidden="true">↗</span></RouterLink>
    </aside>
    <div class="world-main">
      <header v-if="selected" class="selected-head">
        <div class="selected-info">
          <h2>{{ selected.name }}</h2>
          <p>{{ selected.description || '开始投入时间，这座山会记录你的每一步。' }}</p>
        </div>
        <div class="selected-status" aria-label="山屿进度">
          <span class="status-count"><strong>{{ selected.unlocked_count }}</strong><span> / {{ totalTileCount }} 地块</span></span>
          <span class="status-track" role="progressbar" :aria-valuenow="selected.unlocked_count" :aria-valuemin="0" :aria-valuemax="totalTileCount" :aria-label="`已解锁 ${selected.unlocked_count} / ${totalTileCount} 块地形`"><i :style="{ width: `${progressPercent(selected.unlocked_count)}%` }"></i></span>
        </div>
        <div class="selected-actions">
          <button type="button" aria-label="编辑目标" title="编辑目标" @click="openEdit"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5 4 4M4 20l4.2-.9L19 8.3a2.1 2.1 0 0 0-3-3L5.2 16.1 4 20Z" /></svg></button>
          <button class="archive-action" type="button" aria-label="归档目标" title="归档目标" @click="archive"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 4h18v3H3zM9 11h6" /></svg></button>
        </div>
      </header>
      <div v-if="selected" class="focus-bar">
        <strong>开始一段专注</strong>
        <label for="focus-minutes">时长</label>
        <input id="focus-minutes" v-model.number="focusMinutes" type="number" min="1" max="240" :disabled="focusBusy" aria-label="专注时长（分钟）" />
        <span>分钟</span>
        <button type="button" :disabled="focusBusy" @click="startFocus">{{ focusBusy ? '准备中…' : '开始专注' }}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 9 6-9 6z" /></svg></button>
      </div>
      <div class="island-stage">
        <VoxelIsland v-if="selected" :key="selected.id" :tiles="tiles" :unlocked-count="selected.unlocked_count" :palette="palettes[selected.palette_variant]" :selected-order="selectedTile?.unlockOrder ?? null" @select="selectedTile = $event" />
        <div v-else class="empty-stage"><p>你的第一座山屿即将出现在这里。</p><button type="button" @click="openCreate">新建目标</button></div>
        <p v-if="selectedTile" class="tile-detail">{{ tileLabels[selectedTile.kind] }} <span>·</span> 第 {{ selectedTile.unlockOrder }} 块 <span>·</span> 海拔 {{ selectedTile.elevation.toFixed(1) }}</p>
      </div>
    </div>
    <div v-if="showForm" class="form-backdrop" @click.self="showForm = false"><form class="goal-form" @submit.prevent="save"><h2>{{ editing ? '编辑目标' : '新建目标' }}</h2><label for="goal-name">目标名称</label><input id="goal-name" v-model="name" required maxlength="120" autofocus /><label for="goal-description">描述（选填）</label><textarea id="goal-description" v-model="description" maxlength="2000" rows="3"></textarea><label for="goal-palette">山色</label><select id="goal-palette" v-model="palette"><option value="jade">青绿</option><option value="azurite">石青</option><option value="ochre">赭石</option><option value="pale">浅绢</option></select><label for="goal-target">每周目标分钟（选填）</label><input id="goal-target" v-model.number="weeklyTarget" type="number" min="1" max="10080" /><p v-if="error" class="world-error" role="alert">{{ error }}</p><div class="form-actions"><button type="button" @click="showForm = false">取消</button><button type="submit" :disabled="pending">{{ pending ? '保存中…' : '保存目标' }}</button></div></form></div>
  </section>
</template>

<style scoped>
.world-page{display:grid;grid-template-columns:292px minmax(0,1fr);min-height:calc(100vh - 72px);min-height:calc(100svh - 72px);background:#081712;color:var(--ink)}
.goal-rail{display:flex;flex-direction:column;min-height:calc(100vh - 72px);padding:30px 20px 22px;border-right:1px solid var(--line);background:rgba(255,255,255,0.03)}
.rail-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.rail-head h1,.selected-head h2,.goal-form h2{font-family:"Noto Serif SC",Georgia,serif;font-weight:500}
.rail-head h1{margin:0;font-size:25px;line-height:1.2}
.rail-head p{margin:6px 0 0;color:var(--faint);font-size:13px}
.add-button{display:grid;place-items:center;width:40px;height:40px;flex:none;border:0;border-radius:6px;background:var(--accent);color:#071712;cursor:pointer}
.add-button svg,.selected-actions svg,.focus-bar button svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.add-button:hover,.focus-bar button:hover{background:var(--accent-strong)}
.goal-list{display:grid;gap:5px;list-style:none;margin:28px 0 0;padding:0}
.goal-list button{display:flex;align-items:center;gap:12px;width:100%;min-height:72px;padding:11px 10px;border:1px solid transparent;border-radius:6px;background:transparent;color:inherit;text-align:left;cursor:pointer}
.goal-list button:hover{background:rgba(255,255,255,0.06)}
.goal-list button.active{border-color:rgba(143,214,176,0.35);background:rgba(143,214,176,0.08)}
.goal-mark{width:30px;height:30px;flex:none;border:1px solid rgba(255,255,255,0.16);border-radius:3px;background:var(--goal-color)}
.goal-copy{display:block;flex:1;min-width:0}
.goal-list strong,.goal-list small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.goal-list strong{font-size:14px;font-weight:650}
.goal-list small{margin-top:4px;color:var(--faint);font-size:11px;font-variant-numeric:tabular-nums}
.goal-progress,.status-track{display:block;height:3px;overflow:hidden;background:rgba(255,255,255,0.12)}
.goal-progress{margin-top:8px}
.goal-progress i,.status-track i{display:block;height:100%;background:var(--accent)}
.rail-message{margin:26px 2px 0;color:var(--muted);font-size:13px;line-height:1.75}
.demo-link{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:auto;padding:15px 2px 0;border-top:1px solid var(--line);color:var(--accent);text-decoration:none;font-size:13px}
.demo-link span{font-size:16px}
.world-main{display:flex;flex-direction:column;min-width:0;min-height:calc(100vh - 72px)}
.selected-head{display:flex;align-items:center;gap:26px;min-height:132px;padding:22px 4vw 18px}
.selected-info{flex:1;min-width:0}
.selected-head h2{overflow-wrap:anywhere;margin:0 0 8px;font-size:30px;line-height:1.2}
.selected-info p{max-width:66ch;margin:0;color:var(--muted);font-size:13px;line-height:1.6}
.selected-status{display:grid;gap:8px;width:150px;flex:none}
.status-count{display:flex;align-items:baseline;gap:5px;color:var(--faint);font-size:12px;font-variant-numeric:tabular-nums}
.status-count strong{color:var(--ink);font-family:"Noto Serif SC",Georgia,serif;font-size:25px;font-weight:500}
.status-track{width:100%}
.status-count span{white-space:nowrap}
.selected-actions{display:flex;gap:5px;align-self:flex-start}
.selected-actions button{display:grid;place-items:center;width:38px;height:38px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--muted);cursor:pointer}
.selected-actions button:hover{background:rgba(255,255,255,0.08)}
.selected-actions button.archive-action:hover{border-color:rgba(224,138,125,0.5);background:rgba(224,138,125,0.12);color:#e08a7d}
.island-stage{position:relative;flex:1;min-height:560px;overflow:hidden;background:radial-gradient(80% 55% at 68% 28%,rgba(143,214,176,0.10) 0%,rgba(143,214,176,0) 60%),linear-gradient(180deg,#0e2620 0%,#0a1d17 60%,#081712 100%)}
.empty-stage{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;color:var(--muted)}
.empty-stage p{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-size:21px}
.empty-stage button{min-height:40px;padding:0 16px;border:0;border-radius:6px;background:var(--accent);color:#071712;font:inherit;cursor:pointer}
.tile-detail{position:absolute;left:3vw;bottom:20px;margin:0;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.tile-detail span{padding:0 5px;color:var(--faint)}
.focus-bar{display:flex;align-items:center;gap:10px;min-height:62px;padding:0 4vw 14px;color:var(--muted)}
.focus-bar strong{margin-right:8px;font-size:13px;font-weight:650}
.focus-bar label{color:var(--faint);font-size:12px}
.focus-bar input{width:64px;height:38px;padding:0 9px;border:1px solid var(--line);border-radius:5px;background:rgba(255,255,255,0.05);color:var(--ink);font:inherit;font-variant-numeric:tabular-nums}
.focus-bar>span{margin-left:-4px;color:var(--faint);font-size:12px}
.focus-bar button{display:inline-flex;align-items:center;gap:9px;min-height:40px;margin-left:8px;padding:0 14px;border:0;border-radius:6px;background:var(--accent);color:#071712;font:inherit;font-size:13px;font-weight:650;cursor:pointer}
.focus-bar button svg{width:15px;height:15px;fill:currentColor;stroke:none}
.focus-bar button:disabled{opacity:.58;cursor:wait}
.form-backdrop{position:fixed;inset:0;z-index:30;display:grid;place-items:center;padding:16px;background:rgba(4,12,9,0.72)}
.goal-form{display:flex;flex-direction:column;width:min(100%,460px);max-height:95vh;overflow:auto;padding:28px;background:#0c211a;border:1px solid var(--line);border-radius:8px;box-shadow:0 16px 40px rgba(0,0,0,0.45)}
.goal-form h2{margin:0 0 12px;font-size:25px}
.goal-form label{margin:13px 0 6px;font-size:13px;font-weight:650}
.goal-form input,.goal-form textarea,.goal-form select{padding:10px;border:1px solid var(--line);border-radius:5px;background:rgba(255,255,255,0.05);color:var(--ink);font:inherit}
.form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}
.form-actions button{min-height:40px;padding:0 14px;border-radius:5px;font:inherit;font-size:13px;cursor:pointer}
.form-actions button:first-child{border:1px solid var(--line);background:transparent;color:var(--ink)}
.form-actions button:last-child{border:0;background:var(--accent);color:#071712;font-weight:650}
.form-actions button:disabled{opacity:.55;cursor:wait}
.world-error{color:#e08a7d;font-size:13px}
.world-page button:focus-visible,.world-page input:focus-visible,.world-page select:focus-visible,.world-page textarea:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
@media(max-width:900px){
  .world-page{grid-template-columns:248px minmax(0,1fr)}
  .goal-rail{padding:24px 14px 18px}
  .selected-head{gap:16px;padding-right:24px;padding-left:24px}
  .selected-status{width:116px}
  .selected-head h2{font-size:26px}
  .focus-bar{padding-right:24px;padding-left:24px}
}
@media(max-width:700px){
  .world-page{grid-template-columns:minmax(0,1fr);min-height:calc(100vh - 64px);min-height:calc(100svh - 64px)}
  .goal-rail{min-height:0;padding:16px 18px 12px;border-right:0;border-bottom:1px solid var(--line)}
  .rail-head h1{font-size:21px}
  .rail-head p{margin-top:3px}
  .add-button{width:38px;height:38px}
  .goal-list{display:flex;gap:6px;overflow-x:auto;margin:13px -18px 0;padding:0 18px 3px;scrollbar-width:thin}
  .goal-list li{min-width:166px;max-width:220px;flex:1}
  .goal-list button{min-height:58px;padding:8px}
  .goal-mark{width:24px;height:24px}
  .goal-list small{font-size:10px}
  .goal-progress{margin-top:5px}
  .demo-link{display:none}
  .world-main{min-height:calc(100vh - 64px)}
  .selected-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 14px;min-height:0;padding:17px 18px 10px}
  .selected-info{grid-column:1 / -1}
  .selected-head h2{margin-bottom:4px;font-size:24px}
  .selected-info p{font-size:12px}
  .selected-status{grid-template-columns:auto minmax(70px,1fr);align-items:center;gap:9px;width:auto;min-width:0}
  .status-count strong{font-size:20px}
  .status-count{font-size:11px}
  .selected-actions{grid-column:2;grid-row:2;align-self:center}
  .selected-actions button{width:36px;height:36px}
  .focus-bar{gap:8px;min-height:58px;padding:4px 18px 10px}
  .focus-bar strong{margin-right:auto;font-size:12px}
  .focus-bar label{display:none}
  .focus-bar input{width:58px;height:36px}
  .focus-bar>span{font-size:11px}
  .focus-bar button{min-height:38px;margin-left:0;padding:0 10px;font-size:12px}
  .island-stage{min-height:420px;min-height:calc(100svh - 250px)}
  .tile-detail{left:18px;bottom:12px;font-size:11px}
}
@media(max-width:420px){
  .selected-status{grid-template-columns:1fr;gap:4px}
  .status-track{max-width:130px}
  .focus-bar{gap:6px}
  .focus-bar strong{max-width:86px;line-height:1.3}
  .focus-bar button{gap:5px;padding:0 8px}
  .island-stage{min-height:360px;min-height:calc(100svh - 272px)}
}
</style>
