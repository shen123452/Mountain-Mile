<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useReveal } from './useReveal'

const { target, style } = useReveal()

// 与首页「过程完全可见」同源的运行记录示例
const runEntries = [
  { kind: '思考', text: '本周英语目标落后 40 分钟,先看今日到期任务与复习队列。' },
  { kind: '工具', text: 'getTodayTasks → 2 个任务到期、1 张复习卡到期' },
  { kind: '审批', text: 'scheduleReview 是低风险写入,当前档位下自动执行' },
  { kind: '结果', text: '已排定 3 天后的复习,并写入运行记录,可随时回放。' },
]
</script>

<template>
  <section ref="target" class="lm-band lm-featured" aria-labelledby="featured-title">
    <div class="lm-featured-inner">
      <h2 id="featured-title" class="sr-only">过程完全可见</h2>
      <div class="lm-panel lm-card" :style="style({ duration: 0.9, distance: 60 })">
        <div class="lm-run">
          <header class="lm-run-head">
            <span class="lm-run-name">运行 #12 · 英语 30 分钟阅读目标</span>
            <span class="lm-run-chip">可回放</span>
          </header>
          <ol class="lm-run-list">
            <li v-for="(entry, index) in runEntries" :key="entry.kind" :style="{ '--order': index }">
              <span class="lm-run-kind">{{ entry.kind }}</span>
              <p>{{ entry.text }}</p>
            </li>
          </ol>
        </div>

        <div class="lm-panel-foot">
          <div class="lm-approach">
            <p class="lm-approach-label">我们的方法</p>
            <p class="lm-approach-text">
              思考、工具调用与结果以 SSE 实时流式呈现,并持久化到运行记录;
              断线可补齐、随时可回放,像看山间云雾一样观察 agent 的每一步。
            </p>
          </div>
          <RouterLink to="/observatory" class="lm-explore">看观测台</RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lm-featured{padding:clamp(1.5rem,4vw,3rem) clamp(1.25rem,5vw,4rem) clamp(4.5rem,9vw,7.5rem)}
.lm-featured-inner{max-width:1180px;margin:0 auto}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}

.lm-panel{position:relative;border-radius:14px;overflow:hidden}
.lm-run{padding:clamp(1.25rem,3vw,2rem)}
.lm-run-head{display:flex;align-items:center;gap:.75rem;margin-bottom:1rem}
.lm-run-name{font-weight:700;color:var(--lm-ink);font-size:.95rem}
.lm-run-chip{padding:.2rem .6rem;border-radius:999px;background:rgba(143,214,176,0.12);color:var(--lm-accent);font-size:.72rem;font-weight:700}
.lm-run-list{list-style:none;margin:0;padding:0;display:grid;gap:.6rem}
.lm-run-list li{display:grid;grid-template-columns:4.2rem minmax(0,1fr);gap:.9rem;align-items:baseline;padding:.85rem 1rem;border:1px solid rgba(255,255,255,0.08);border-radius:10px;background:rgba(255,255,255,0.04);animation:lm-run-in .5s ease-out both;animation-delay:calc(150ms + var(--order) * 140ms)}
.lm-run-kind{color:var(--lm-accent);font-size:.78rem;font-weight:700}
.lm-run-list p{margin:0;color:var(--lm-muted);font-size:.88rem;line-height:1.7}

.lm-panel-foot{display:flex;flex-direction:column;gap:1rem;padding:clamp(1.25rem,3vw,2rem);border-top:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);align-items:flex-start}
.lm-approach{max-width:46rem}
.lm-approach-label{margin:0 0 .6rem;color:var(--lm-accent);font-size:.72rem;font-weight:700;letter-spacing:.16em}
.lm-approach-text{margin:0;color:var(--lm-muted);font-size:.92rem;line-height:1.8}
.lm-explore{display:inline-flex;align-items:center;min-height:2.75rem;padding:0 1.5rem;border-radius:999px;background:var(--lm-accent);color:#071712;font:inherit;font-size:.88rem;font-weight:650;text-decoration:none;transition:transform .25s ease,background .18s ease}
.lm-explore:hover{background:#a5e0c1;transform:scale(1.03)}
.lm-explore:active{transform:scale(.95)}

@keyframes lm-run-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media(max-width:620px){
  .lm-run-list li{grid-template-columns:minmax(0,1fr);gap:.3rem}
}
@media(prefers-reduced-motion:reduce){
  .lm-run-list li{animation:none}
  .lm-explore{transition:background .18s ease}
}
</style>
