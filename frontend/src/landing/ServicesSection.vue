<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ArrowUpRight } from '@lucide/vue'
import { useReveal } from './useReveal'

const { target: headerTarget, style: headerStyle } = useReveal()
const { target: gridTarget, inView: gridInView } = useReveal()

const cards = [
  {
    tag: '规划 · 执行',
    title: '五人小队,审批把关',
    description:
      '规划者、执行者、复盘者、记忆官、向导各管一段,按请求自动路由、互相委派;关键写入由审批把门,每一步落库可查。',
    to: '/agent',
    cta: '看向导工作台',
    accent: '#8fd6b0',
  },
  {
    tag: '沉淀 · 复习',
    title: '有节奏的记忆',
    description:
      'SM-2 间隔复习自动排程;专注分钟与打卡天数解锁山屿地块——群岛的地形,就是你真实投入结构的等高线图。',
    to: '/observatory',
    cta: '看观测台',
    accent: '#d9b877',
  },
]

function cardStyle(delay: number) {
  const shown = gridInView.value
  return shown
    ? {
        opacity: 1,
        transform: 'translateY(0px)',
        transition: `opacity 0.8s ease ${delay}s, transform 0.8s ease ${delay}s`,
      }
    : {
        opacity: 0,
        transform: 'translateY(50px)',
        transition: 'none',
      }
}
</script>

<template>
  <section ref="headerTarget" class="lm-band lm-services" aria-labelledby="services-title">
    <div class="lm-services-inner">
      <div class="lm-services-head" :style="headerStyle({ duration: 0.7, distance: 30 })">
        <h2 id="services-title">它能做什么</h2>
        <p class="lm-services-label">五个角色 · 两种沉淀 · 一座山</p>
      </div>

      <div ref="gridTarget" class="lm-services-grid">
        <article v-for="(card, index) in cards" :key="card.tag" class="lm-card" :style="cardStyle(index * 0.15)">
          <div class="lm-card-top">
            <span class="lm-card-tag" :style="{ color: card.accent }">{{ card.tag }}</span>
            <span class="lm-card-icon" :style="{ borderColor: card.accent + '55' }">
              <ArrowUpRight :size="16" :style="{ color: card.accent }" />
            </span>
          </div>
          <h3 class="lm-card-title">{{ card.title }}</h3>
          <p class="lm-card-desc">{{ card.description }}</p>
          <RouterLink :to="card.to" class="lm-card-cta">
            {{ card.cta }}
            <ArrowUpRight :size="14" />
          </RouterLink>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lm-services{padding:clamp(4.5rem,9vw,7.5rem) clamp(1.25rem,5vw,4rem)}
.lm-services-inner{max-width:1180px;margin:0 auto}
.lm-services-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:clamp(2rem,4vw,3rem)}
.lm-services-head h2{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.6rem,3.4vw,2.4rem);color:var(--lm-ink)}
.lm-services-label{color:var(--lm-faint);font-size:.8rem;letter-spacing:.12em}

.lm-services-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(1rem,2.5vw,1.5rem)}
.lm-card{display:grid;gap:.9rem;padding:clamp(1.25rem,3vw,2rem);border-radius:12px;transition:box-shadow .2s ease,transform .2s ease}
.lm-card:hover{box-shadow:0 28px 60px rgba(0,0,0,.42);transform:translateY(-2px)}
.lm-card-top{display:flex;align-items:center;justify-content:space-between}
.lm-card-tag{font-size:.72rem;font-weight:700;letter-spacing:.14em}
.lm-card-icon{display:grid;place-items:center;width:2rem;height:2rem;border-radius:999px;border:1px solid;background:rgba(255,255,255,0.06)}
.lm-card-title{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.15rem,2vw,1.4rem);color:var(--lm-ink)}
.lm-card-desc{margin:0;color:var(--lm-muted);font-size:.9rem;line-height:1.8}
.lm-card-cta{display:inline-flex;align-items:center;gap:.35rem;margin-top:.25rem;color:var(--lm-accent);font-size:.86rem;font-weight:650;text-decoration:none}
.lm-card-cta:hover{color:#a5e0c1;text-decoration:underline;text-underline-offset:3px}

@media(max-width:760px){
  .lm-services-grid{grid-template-columns:minmax(0,1fr)}
  .lm-services-label{display:none}
}
</style>
