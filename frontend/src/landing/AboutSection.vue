<script setup lang="ts">
import { useReveal } from './useReveal'

const { target, style } = useReveal()
</script>

<template>
  <section ref="target" class="lm-band lm-about" aria-labelledby="about-title">
    <div class="lm-about-inner">
      <p class="lm-label" :style="style({ duration: 0.6, distance: 20 })">山程 · 定位</p>
      <h2 id="about-title" class="lm-about-h" :style="style({ duration: 0.8, delay: 0.1 })">
        为会思考的学习,<br class="lm-br" />
        <span class="lm-accent">造一座生长的山屿。</span>
      </h2>
      <p class="lm-about-sub" :style="style({ duration: 0.7, delay: 0.2, distance: 20 })">
        不是多一个聊天框,而是一台会把学习事务真正跑完的机器。
      </p>
    </div>
  </section>
</template>

<style scoped>
.lm-about{position:relative;overflow:hidden;padding:clamp(4.5rem,9vw,7.5rem) clamp(1.25rem,5vw,4rem);text-align:center}
.lm-about::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at top,rgba(217,184,119,0.07) 0%,transparent 70%);pointer-events:none}
.lm-about-inner{position:relative;max-width:900px;margin:0 auto}
.lm-label{margin:0 0 1.2rem;color:var(--lm-accent);font-size:.8rem;font-weight:700;letter-spacing:.18em}
.lm-about-h{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.9rem,4.5vw,3.4rem);line-height:1.3;color:var(--lm-ink)}
.lm-accent{color:var(--lm-gold)}
.lm-about-sub{margin:1.2rem auto 0;max-width:34rem;color:var(--lm-muted);line-height:1.85}
@media(max-width:620px){.lm-br{display:none}}
</style>
