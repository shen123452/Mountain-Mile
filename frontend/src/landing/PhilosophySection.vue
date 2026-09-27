<script setup lang="ts">
import { useReveal } from './useReveal'

const { target: headingTarget, style: headingStyle } = useReveal()
const { target: leftTarget, inView: leftInView } = useReveal()
const { target: rightTarget, inView: rightInView } = useReveal()

function slide(axis: 'left' | 'right', shown: boolean) {
  return shown
    ? {
        opacity: 1,
        transform: 'translateX(0px)',
        transition: 'opacity 0.9s ease, transform 0.9s ease',
      }
    : {
        opacity: 0,
        transform: axis === 'left' ? 'translateX(-40px)' : 'translateX(40px)',
        transition: 'none',
      }
}
</script>

<template>
  <section ref="headingTarget" class="lm-band lm-philosophy" aria-labelledby="philosophy-title">
    <div class="lm-philosophy-inner">
      <h2 id="philosophy-title" class="lm-philosophy-h" :style="headingStyle({ duration: 0.8 })">
        地形即数据
        <span class="lm-times">×</span>
        过程可回放
      </h2>

      <div class="lm-philosophy-grid">
        <div ref="leftTarget" class="lm-philosophy-left" :style="slide('left', leftInView)">
          <div class="lm-formula lm-card">
            <code>解锁地块 = 20 + ⌊专注分钟 ÷ 8⌋ + 打卡天数 × 3</code>
            <p>每块解锁地块都能追溯回一次专注、一次打卡或一条记忆;群岛的高低,就是你真实的投入结构。</p>
          </div>
        </div>

        <div ref="rightTarget" class="lm-philosophy-right" :style="slide('right', rightInView)">
          <div>
            <p class="lm-block-label">自主档位</p>
            <p class="lm-block-text">
              只读观察先行,写入分级放行:低风险写入(如排定复习)在 L1 档位自动执行,
              关键操作永远停下等你确认。你可以随时调低档位、中断运行。
            </p>
          </div>
          <div class="lm-divider" aria-hidden="true"></div>
          <div>
            <p class="lm-block-label">完全可审计</p>
            <p class="lm-block-text">
              思考、工具调用与结果全部持久化到运行记录,断线可补齐、随时可回放;
              在观测台里逐步回看 agent 的每一次决定。
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lm-philosophy{padding:clamp(4.5rem,9vw,7.5rem) clamp(1.25rem,5vw,4rem)}
.lm-philosophy-inner{max-width:1180px;margin:0 auto}
.lm-philosophy-h{margin:0 0 clamp(2.5rem,5vw,4rem);font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(2.2rem,5vw,3.8rem);line-height:1.2;color:var(--lm-ink)}
.lm-times{font-family:"Noto Serif SC",Georgia,serif;font-style:italic;color:var(--lm-gold);margin:0 .35em;font-weight:400}

.lm-philosophy-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(1.5rem,4vw,3rem)}
.lm-formula{padding:1.5rem;height:100%;display:grid;gap:1rem;align-content:start}
.lm-formula code{display:inline-block;padding:.6rem .8rem;border-radius:8px;background:rgba(255,255,255,0.06);color:var(--lm-accent);font-size:.86rem}
.lm-formula p{margin:0;color:var(--lm-muted);font-size:.9rem;line-height:1.8}

.lm-philosophy-right{display:grid;gap:0;align-content:center}
.lm-block-label{margin:0 0 .7rem;color:var(--lm-accent);font-size:.74rem;font-weight:700;letter-spacing:.14em}
.lm-block-text{margin:0;color:var(--lm-muted);font-size:clamp(.95rem,1.5vw,1.05rem);line-height:1.85}
.lm-divider{width:100%;height:1px;background:rgba(255,255,255,0.1);margin:clamp(1.5rem,4vw,2.5rem) 0}

@media(max-width:760px){
  .lm-philosophy-grid{grid-template-columns:minmax(0,1fr)}
}
</style>
