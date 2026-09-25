<script setup lang="ts">
import { onMounted, ref } from 'vue'

interface Ranking { id: string; name: string; unlocked: number; total: number; progress: number }
interface Summary { total_focus_minutes: number; total_focus_sessions: number; total_checkins: number; current_streak: number; active_goals: number; due_reviews: number; goal_ranking: Ranking[] }
interface TrendPoint { date: string; minutes: number }
interface HeatCell { date: string; minutes: number; level: number }

const summary = ref<Summary | null>(null)
const trend = ref<TrendPoint[]>([])
const heatCells = ref<HeatCell[]>([])
const error = ref('')

async function request<T>(path: string) { const response = await fetch(`/api/stats${path}`, { credentials: 'include' }); const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.error?.message ?? '请求失败'); return body.data as T }
function maxMinutes() { return Math.max(15, ...trend.value.map(point => point.minutes)) }
function barHeight(minutes: number) { return `${Math.max(4, Math.round((minutes / maxMinutes()) * 100))}%` }
function heatColumns() { const columns: HeatCell[][] = []; heatCells.value.forEach((cell, index) => { const column = Math.floor(index / 7); (columns[column] ??= []).push(cell) }); return columns }
function formatHours(minutes: number) { return minutes >= 60 ? `${(minutes / 60).toFixed(1)}h` : `${minutes}min` }

onMounted(() => {
  void Promise.all([request<Summary>('/summary'), request<{ points: TrendPoint[] }>('/trend?days=14'), request<{ cells: HeatCell[] }>('/heatmap?weeks=26')])
    .then(([summaryData, trendData, heatData]) => { summary.value = summaryData; trend.value = trendData.points; heatCells.value = heatData.cells })
    .catch(cause => { error.value = cause instanceof Error ? cause.message : '加载失败' })
})
</script>

<template>
  <section class="stats-page">
    <header class="stats-heading"><div><p>山志</p><h1>每一步,都留在山上</h1><span>专注、打卡与生长,汇成你的学习地形。</span></div></header>
    <p v-if="error" class="stats-error" role="alert">{{ error }}</p>
    <template v-if="summary">
      <div class="totals-grid">
        <article class="total-card"><small>累计专注</small><strong>{{ formatHours(summary.total_focus_minutes) }}</strong><em>{{ summary.total_focus_sessions }} 次</em></article>
        <article class="total-card"><small>连续打卡</small><strong>{{ summary.current_streak }} 天</strong><em>累计 {{ summary.total_checkins }} 天</em></article>
        <article class="total-card"><small>活跃目标</small><strong>{{ summary.active_goals }}</strong></article>
        <article class="total-card"><small>待复习</small><strong>{{ summary.due_reviews }}</strong><em>到期复习卡</em></article>
      </div>

      <section class="panel"><div class="panel-head"><h2>近 14 天专注</h2><span>分钟 / 天</span></div>
        <div class="trend-chart">
          <div v-for="point in trend" :key="point.date" class="trend-bar" :title="`${point.date} · ${point.minutes} 分钟`">
            <i :style="{ height: barHeight(point.minutes) }"></i><span>{{ point.date.slice(5) }}</span>
          </div>
        </div>
      </section>

      <section class="panel"><div class="panel-head"><h2>半年热力</h2><span>颜色越深,专注越久</span></div>
        <div class="heatmap">
          <div v-for="(column, index) in heatColumns()" :key="index" class="heatmap-column">
            <i v-for="cell in column" :key="cell.date" :data-level="cell.level" :title="`${cell.date} · ${cell.minutes} 分钟`"></i>
          </div>
        </div>
      </section>

      <section class="panel"><div class="panel-head"><h2>目标排行</h2><span>按山屿生长排序</span></div>
        <p v-if="!summary.goal_ranking.length" class="panel-empty">还没有目标,去群岛创建一座山吧。</p>
        <ul v-else class="ranking-list">
          <li v-for="(goal, index) in summary.goal_ranking" :key="goal.id">
            <span class="rank">#{{ index + 1 }}</span>
            <span class="rank-name">{{ goal.name }}</span>
            <span class="rank-bar"><i :style="{ width: `${Math.round(goal.progress * 100)}%` }"></i></span>
            <span class="rank-meta">{{ goal.unlocked }}/{{ goal.total }}</span>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>

<style scoped>
.stats-page{max-width:1180px;margin:0 auto;padding:clamp(2rem,5vw,4rem) clamp(1.25rem,5vw,4rem);color:#173b36}
.stats-heading{padding-bottom:2rem;border-bottom:1px solid #d6e3d6}.stats-heading p{margin:0 0 .5rem;color:#4b8f73;font-size:.78rem;font-weight:700;letter-spacing:.1em}.stats-heading h1{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.8rem,4vw,3.2rem)}.stats-heading span{display:block;margin-top:.7rem;color:#5f756d}
.stats-error{margin:1rem 0 0;color:#8b5247}
.totals-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin-top:1.5rem}
.total-card{padding:1rem 1.2rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}.total-card small{color:#70877d;font-size:.74rem}.total-card strong{display:block;margin-top:.35rem;font-family:"Noto Serif SC",Georgia,serif;font-size:1.55rem;font-weight:600}.total-card em{display:block;margin-top:.25rem;color:#8aa195;font-size:.7rem;font-style:normal}
.panel{margin-top:1.25rem;padding:1.2rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}
.panel-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1rem}.panel-head h2{margin:0;font-size:1rem}.panel-head span{color:#70877d;font-size:.75rem}
.panel-empty{margin:0;color:#678075;font-size:.85rem}
.trend-chart{display:flex;align-items:flex-end;gap:6px;height:140px}
.trend-bar{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;flex:1;min-width:0;height:100%}
.trend-bar i{display:block;width:100%;max-width:34px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#4b8f73,#285d4e)}
.trend-bar span{color:#8aa195;font-size:.66rem;white-space:nowrap}
.heatmap{display:flex;gap:3px;overflow-x:auto;padding-bottom:.4rem}
.heatmap-column{display:flex;flex-direction:column;gap:3px}
.heatmap-column i{width:12px;height:12px;border-radius:3px;background:#e8efe6}
.heatmap-column i[data-level="1"]{background:#bcd8c4}.heatmap-column i[data-level="2"]{background:#86bda0}.heatmap-column i[data-level="3"]{background:#4b8f73}.heatmap-column i[data-level="4"]{background:#285d4e}
.ranking-list{list-style:none;margin:0;padding:0}
.ranking-list li{display:flex;align-items:center;gap:.9rem;padding:.65rem 0;border-top:1px solid #e0e9df}
.rank{color:#8aa195;font-size:.78rem;width:2rem;flex-shrink:0}
.rank-name{flex-shrink:0;max-width:12rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.9rem}
.rank-bar{flex:1;height:8px;border-radius:999px;background:#e3ecdf;overflow:hidden}
.rank-bar i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#4b8f73,#285d4e)}
.rank-meta{flex-shrink:0;color:#70877d;font-size:.74rem}
</style>
