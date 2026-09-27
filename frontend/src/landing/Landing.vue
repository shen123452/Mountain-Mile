<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import VoxelIsland from '../components/three/VoxelIsland.vue'
import { generateTerrain } from '../components/three/terrain'
import { palettes } from '../components/three/palettes'
import AboutSection from './AboutSection.vue'
import FeaturedSection from './FeaturedSection.vue'
import PhilosophySection from './PhilosophySection.vue'
import ServicesSection from './ServicesSection.vue'

const auth = useAuthStore()

// 固定场景层:与 /terrain-demo 同源的确定性地形,半生长状态,作为整页「夜山」背景
const skyTiles = generateTerrain({ seed: 'mountain-mile-landing' })
const skyUnlocked = Math.max(40, Math.round(skyTiles.length * 0.5))
const jade = palettes.jade
</script>

<template>
  <div class="lm">
    <!-- 固定场景层:夜空 + 3D 山屿(整页都在这个"世界"里) -->
    <div class="lm-sky" aria-hidden="true">
      <VoxelIsland :tiles="skyTiles" :unlocked-count="skyUnlocked" :palette="jade" />
    </div>

    <div class="lm-content">
      <!-- 1 · 首屏:场景全开,文案靠左 -->
      <section class="lm-hero" aria-labelledby="lm-title">
        <div class="lm-hero-veil" aria-hidden="true"></div>
        <div class="lm-hero-inner">
          <div class="lm-copy">
            <p class="lm-eyebrow">agent 优先的学习成长应用</p>
            <h1 id="lm-title">学习如<em class="lm-word">登山</em>,<br>每一步都算数。</h1>
            <p class="lm-lede">
              一支五人学习智能体小队,观察你的学习数据、调用工具制定并推进计划、在关键写入前请你确认;
              每个目标,都是一座随之生长的青绿山屿。
            </p>
            <div class="lm-actions">
              <RouterLink v-if="!auth.user" class="lm-btn primary" to="/register">免费开始</RouterLink>
              <RouterLink v-else class="lm-btn primary" to="/world">进入群岛</RouterLink>
              <RouterLink class="lm-btn ghost" :to="auth.user ? '/agent' : '/login'">看向导工作台</RouterLink>
            </div>
            <p class="lm-note">登录后即可创建目标、开始专注与打卡;全过程可审计、可回放、可中断。</p>
          </div>
        </div>
      </section>

      <!-- 2-5 · 玻璃分节 -->
      <AboutSection />
      <FeaturedSection />
      <PhilosophySection />
      <ServicesSection />

      <!-- 收尾 CTA -->
      <section class="lm-band lm-close" aria-labelledby="lm-close-title">
        <div class="lm-close-inner">
          <h2 id="lm-close-title">从第一个目标,开始你的群岛。</h2>
          <p class="lm-close-sub">地形即数据,过程即记忆。每解锁一块地,都能追溯回一次专注、一次打卡或一条记忆。</p>
          <div class="lm-actions">
            <RouterLink v-if="!auth.user" class="lm-btn primary" to="/register">创建第一个目标</RouterLink>
            <RouterLink v-else class="lm-btn primary" to="/world">回到我的群岛</RouterLink>
            <RouterLink class="lm-btn ghost" to="/terrain-demo">先看山屿演示</RouterLink>
          </div>
        </div>
      </section>

      <footer class="lm-band lm-footer">
        <div class="lm-footer-inner">
          <span>山程 · Mountain Mile — agent 优先的学习成长应用</span>
          <span>学习如登山,每一步都算数。</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.lm-content{position:relative;z-index:10}

/* ── 首屏:场景全开 + 左侧纱(保证文案可读) ── */
.lm-hero{position:relative;min-height:calc(100dvh - 72px);display:flex;align-items:center}
.lm-hero-veil{
  position:absolute;inset:0;pointer-events:none;
  background:
    radial-gradient(88% 92% at 14% 58%,rgba(8,23,18,0.82) 0%,rgba(8,23,18,0.4) 40%,rgba(8,23,18,0) 68%),
    linear-gradient(180deg,rgba(8,23,18,0.55) 0%,rgba(8,23,18,0) 24%,rgba(8,23,18,0) 76%,rgba(8,23,18,0.5) 100%);
}
.lm-hero-inner{position:relative;z-index:1;width:100%;max-width:1180px;margin:0 auto;padding:clamp(3rem,7vw,5rem) clamp(1.25rem,5vw,4rem)}
.lm-copy{max-width:34rem}
.lm-eyebrow{margin:0 0 1.1rem;color:var(--lm-accent);font-size:.78rem;font-weight:700;letter-spacing:.16em}
.lm-hero h1{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(2.3rem,5.2vw,4rem);line-height:1.25;color:var(--lm-ink)}
.lm-word{font-style:normal;color:var(--lm-gold)}
.lm-lede{margin:1.2rem 0 0;max-width:32rem;color:var(--lm-muted);font-size:clamp(.95rem,1.4vw,1.05rem);line-height:1.9}
.lm-note{margin:1.1rem 0 0;color:var(--lm-faint);font-size:.8rem}

/* ── 按钮(落地页胶囊语言) ── */
.lm-actions{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.7rem}
.lm-btn{display:inline-flex;align-items:center;justify-content:center;min-height:2.85rem;padding:0 1.45rem;border-radius:999px;font:inherit;font-size:.9rem;font-weight:600;text-decoration:none;transition:transform .2s ease,background .2s ease,border-color .2s ease}
.lm-btn.primary{background:var(--lm-accent);color:#071712}
.lm-btn.primary:hover{transform:translateY(-1px);background:#a5e0c1}
.lm-btn.ghost{border:1px solid rgba(255,255,255,0.22);color:rgba(242,248,244,0.85)}
.lm-btn.ghost:hover{border-color:rgba(255,255,255,0.45);background:rgba(255,255,255,0.06)}

/* ── 收尾 ── */
.lm-close{padding:clamp(3.5rem,7vw,5rem) clamp(1.25rem,5vw,4rem)}
.lm-close-inner{max-width:44rem;margin:0 auto;text-align:center}
.lm-close h2{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.6rem,3vw,2.2rem);line-height:1.35;color:var(--lm-ink)}
.lm-close-sub{margin:1rem auto 0;max-width:34rem;color:var(--lm-muted);line-height:1.85;font-size:.95rem}
.lm-close .lm-actions{justify-content:center}
.lm-footer{padding:1.5rem clamp(1.25rem,5vw,4rem)}
.lm-footer-inner{max-width:1180px;margin:0 auto;display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem;color:var(--lm-faint);font-size:.76rem}
</style>
