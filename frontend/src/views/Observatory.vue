<script setup lang="ts">
import { onMounted, ref } from 'vue'

interface Totals { runs: number; finished: number; success_rate: number | null; prompt_tokens: number; completion_tokens: number; estimated_cost: number }
interface DailyPoint { date: string; runs: number; prompt_tokens: number; completion_tokens: number; estimated_cost: number }
interface ToolStat { tool: string; calls: number; success_rate: number; avg_latency_ms: number | null }
interface RecentRun { id: string; goal: string; role: string; status: string; current_step: number; prompt_tokens: number; completion_tokens: number; estimated_cost: number; duration_ms: number | null; created_at: string }
interface Metrics { days: number; totals: Totals; daily: DailyPoint[]; tools: ToolStat[]; recent_runs: RecentRun[]; price_note: string }
interface RunStep { number: number; kind: string; role: string; status: string; title: string; detail: string | null }

const metrics = ref<Metrics | null>(null)
const error = ref('')
const expandedId = ref<string | null>(null)
const steps = ref<RunStep[]>([])
const stepsLoading = ref(false)

const statusLabel: Record<string, string> = { completed: '完成', failed: '失败', cancelled: '已中断', rejected: '已拒绝', running: '运行中', queued: '排队中', awaiting_approval: '待审批' }
const roleLabel: Record<string, string> = { Planner: '规划者', Executor: '执行者', Reflector: '复盘者', Curator: '记忆官', Scout: '向导' }

async function request<T>(path: string) { const response = await fetch(`/api${path}`, { credentials: 'include' }); const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.error?.message ?? '请求失败'); return body.data as T }
async function load() { metrics.value = await request<Metrics>('/observatory/metrics?days=14') }
function maxCost() { return Math.max(0.0001, ...(metrics.value?.daily.map(point => point.estimated_cost) ?? [0])) }
function barHeight(cost: number) { return `${Math.max(6, Math.round((cost / maxCost()) * 100))}%` }
function formatDuration(ms: number | null) { if (ms == null) return '—'; return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s` }
function formatDate(iso: string) { return iso.slice(5, 10) }

async function toggleRun(run: RecentRun) {
  if (expandedId.value === run.id) { expandedId.value = null; steps.value = []; return }
  expandedId.value = run.id; steps.value = []; stepsLoading.value = true
  try {
    const detail = await request<{ steps: RunStep[] }>(`/agent/runs/${run.id}`)
    steps.value = detail.steps
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '轨迹加载失败' } finally { stepsLoading.value = false }
}
onMounted(() => { void load().catch(cause => { error.value = cause instanceof Error ? cause.message : '加载失败' }) })
</script>

<template>
  <section class="observatory-page">
    <header class="observatory-heading"><div><p>观测台</p><h1>看见向导的每一步</h1><span>成本、成功率与运行轨迹,全部来自持久化的运行记录。</span></div></header>
    <p v-if="error" class="observatory-error" role="alert">{{ error }}</p>
    <template v-if="metrics">
      <div class="totals-grid">
        <article class="total-card"><small>运行次数(14 天)</small><strong>{{ metrics.totals.runs }}</strong></article>
        <article class="total-card"><small>成功率</small><strong>{{ metrics.totals.success_rate == null ? '—' : `${Math.round(metrics.totals.success_rate * 100)}%` }}</strong></article>
        <article class="total-card"><small>Token 消耗</small><strong>{{ (metrics.totals.prompt_tokens + metrics.totals.completion_tokens).toLocaleString() }}</strong><em>输入 {{ metrics.totals.prompt_tokens.toLocaleString() }} · 输出 {{ metrics.totals.completion_tokens.toLocaleString() }}</em></article>
        <article class="total-card"><small>估算成本</small><strong>¥{{ metrics.totals.estimated_cost.toFixed(4) }}</strong><em>{{ metrics.price_note }}</em></article>
      </div>

      <section class="panel"><div class="panel-head"><h2>成本趋势</h2><span>按日聚合(估算)</span></div>
        <div v-if="metrics.daily.length" class="cost-chart">
          <div v-for="point in metrics.daily" :key="point.date" class="cost-bar" :title="`${point.date} · ¥${point.estimated_cost.toFixed(4)} · ${point.runs} 次运行`">
            <i :style="{ height: barHeight(point.estimated_cost) }"></i><span>{{ formatDate(point.date) }}</span>
          </div>
        </div>
        <p v-else class="panel-empty">近 14 天还没有运行记录,去向导页发起一次试试。</p>
      </section>

      <section class="panel"><div class="panel-head"><h2>工具表现</h2><span>成功率与平均耗时</span></div>
        <table v-if="metrics.tools.length" class="tool-table">
          <thead><tr><th>工具</th><th>调用</th><th>成功率</th><th>平均耗时</th></tr></thead>
          <tbody><tr v-for="tool in metrics.tools" :key="tool.tool"><td><code>{{ tool.tool }}</code></td><td>{{ tool.calls }}</td><td>{{ Math.round(tool.success_rate * 100) }}%</td><td>{{ tool.avg_latency_ms == null ? '—' : `${tool.avg_latency_ms}ms` }}</td></tr></tbody>
        </table>
        <p v-else class="panel-empty">暂无工具调用。</p>
      </section>

      <section class="panel"><div class="panel-head"><h2>最近运行</h2><span>点击展开轨迹回放</span></div>
        <p v-if="!metrics.recent_runs.length" class="panel-empty">暂无运行。</p>
        <ul v-else class="run-list">
          <li v-for="run in metrics.recent_runs" :key="run.id">
            <button type="button" class="run-row" @click="toggleRun(run)">
              <span class="run-status" :data-status="run.status">{{ statusLabel[run.status] ?? run.status }}</span>
              <span class="run-goal">{{ run.goal }}</span>
              <span class="run-meta">{{ roleLabel[run.role] ?? run.role }} · {{ run.current_step }} 步 · {{ formatDuration(run.duration_ms) }} · ¥{{ run.estimated_cost.toFixed(4) }}</span>
            </button>
            <ol v-if="expandedId === run.id" class="step-list">
              <li v-if="stepsLoading" class="step-loading">轨迹加载中…</li>
              <li v-for="step in steps" :key="step.number" :data-kind="step.kind">
                <strong>#{{ step.number }} {{ step.title }}</strong>
                <span>{{ roleLabel[step.role] ?? step.role }} · {{ statusLabel[step.status] ?? step.status }}</span>
                <p v-if="step.detail">{{ step.detail }}</p>
              </li>
            </ol>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>

<style scoped>
.observatory-page{max-width:1180px;margin:0 auto;padding:clamp(2rem,5vw,4rem) clamp(1.25rem,5vw,4rem);color:#173b36}
.observatory-heading{padding-bottom:2rem;border-bottom:1px solid #d6e3d6}.observatory-heading p{margin:0 0 .5rem;color:#4b8f73;font-size:.78rem;font-weight:700;letter-spacing:.1em}.observatory-heading h1{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.8rem,4vw,3.2rem)}.observatory-heading span{display:block;margin-top:.7rem;color:#5f756d}
.observatory-error{margin:1rem 0 0;color:#8b5247}
.totals-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-top:1.5rem}
.total-card{padding:1rem 1.2rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}.total-card small{color:#70877d;font-size:.74rem}.total-card strong{display:block;margin-top:.35rem;font-family:"Noto Serif SC",Georgia,serif;font-size:1.6rem;font-weight:600}.total-card em{display:block;margin-top:.25rem;color:#8aa195;font-size:.7rem;font-style:normal}
.panel{margin-top:1.25rem;padding:1.2rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}
.panel-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1rem}.panel-head h2{margin:0;font-size:1rem}.panel-head span{color:#70877d;font-size:.75rem}
.panel-empty{margin:0;color:#678075;font-size:.85rem}
.cost-chart{display:flex;align-items:flex-end;gap:6px;height:140px}
.cost-bar{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;flex:1;min-width:0;height:100%}
.cost-bar i{display:block;width:100%;max-width:34px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#4b8f73,#285d4e)}
.cost-bar span{color:#8aa195;font-size:.66rem;white-space:nowrap}
.tool-table{width:100%;border-collapse:collapse;font-size:.85rem}.tool-table th{text-align:left;color:#70877d;font-size:.74rem;font-weight:600;padding:.4rem .5rem;border-bottom:1px solid #d4e2d4}.tool-table td{padding:.5rem;border-bottom:1px solid #e6eee4}.tool-table code{background:#e8efe6;padding:.1rem .4rem;border-radius:6px;font-size:.78rem}
.run-list{list-style:none;margin:0;padding:0}
.run-row{display:flex;align-items:center;gap:.9rem;width:100%;padding:.7rem .2rem;border:0;border-top:1px solid #e0e9df;background:transparent;font:inherit;color:inherit;text-align:left;cursor:pointer}
.run-status{flex-shrink:0;padding:.15rem .55rem;border-radius:999px;font-size:.7rem;font-weight:650;background:#e8efe6;color:#285d4e}
.run-status[data-status="failed"],.run-status[data-status="rejected"]{background:#f3e4e0;color:#8b5247}.run-status[data-status="awaiting_approval"]{background:#f4ead3;color:#8a6d2f}.run-status[data-status="cancelled"]{background:#eceee9;color:#70877d}
.run-goal{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.87rem}
.run-meta{flex-shrink:0;color:#70877d;font-size:.74rem}
.step-list{list-style:none;margin:.2rem 0 .8rem;padding:.6rem .9rem;border-left:2px solid #cfe0d2;background:#fdfefa;border-radius:0 8px 8px 0}
.step-list li{padding:.4rem 0;font-size:.82rem}.step-list strong{display:block}.step-list span{color:#70877d;font-size:.72rem}.step-list p{margin:.25rem 0 0;color:#5f756d;font-size:.78rem;white-space:pre-wrap}
.step-loading{color:#8aa195}
</style>
