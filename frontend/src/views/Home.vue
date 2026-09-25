<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const steps = [
  { title: '观察', body: '每次运行前,向导先读取你的计划、待办、今日到期任务与到期复习,形成一份只读快照。', meta: 'getMyPlans · getTodayTasks' },
  { title: '规划', body: '规划者把目标拆成可执行任务;涉及写入的动作默认停下等你确认,低风险写入可在 L1 档位放行。', meta: 'breakdownPlanTasks · 审批' },
  { title: '执行', body: '完成后记录专注分钟、解锁山屿地块、按 SM-2 排定下次复习,每一步落库并可回放。', meta: 'scheduleReview · 生长公式' },
]

const roles = [
  { name: '规划者', desc: '分析学情、制定计划、拆分任务' },
  { name: '执行者', desc: '推进任务、整理待办、记录进展' },
  { name: '复盘者', desc: '复盘投入、分析专注节律' },
  { name: '记忆官', desc: '整理长期记忆与个人资料' },
  { name: '向导', desc: '排定到期复习与提醒' },
]

const timeline = [
  { kind: '思考', text: '本周英语目标落后 40 分钟,先看今日到期任务与复习队列。' },
  { kind: '工具', text: 'getTodayTasks → 2 个任务到期、1 张复习卡到期' },
  { kind: '审批', text: 'scheduleReview 是低风险写入,当前档位下自动执行' },
  { kind: '结果', text: '已排定 3 天后的复习,并写入运行记录,可随时回放。' },
]
</script>

<template>
  <div class="landing">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">agent 优先的学习成长应用</p>
        <h1>学习如登山,<br>每一步都算数。</h1>
        <p class="lede">一支五人学习智能体小队,观察你的学习数据、调用工具制定并推进计划、在关键写入前请你确认;每个目标,都是一座随之生长的青绿山屿。</p>
        <div class="actions">
          <RouterLink v-if="!auth.user" class="button primary" to="/register">免费开始</RouterLink>
          <RouterLink v-else class="button primary" to="/world">进入群岛</RouterLink>
          <RouterLink class="button" :to="auth.user ? '/agent' : '/login'">看向导工作台</RouterLink>
        </div>
        <p class="note">登录后即可创建目标、开始专注与打卡;全过程可审计、可回放、可中断。</p>
      </div>
      <figure class="hero-figure" aria-hidden="true">
        <svg viewBox="0 0 420 320" role="presentation" focusable="false">
          <path d="M0 268 L74 176 L138 246 L206 138 L282 248 L340 196 L420 268 L420 320 L0 320 Z" fill="#2f6b58"/>
          <path d="M0 288 L62 226 L140 286 L214 214 L292 288 L352 246 L420 292 L420 320 L0 320 Z" fill="#4b8f73"/>
          <path d="M0 304 L80 268 L158 306 L236 272 L318 308 L372 284 L420 308 L420 320 L0 320 Z" fill="#8fbda6"/>
          <g fill="none" stroke="#173b36" stroke-width="1.5" stroke-linecap="round" opacity=".45">
            <path d="M96 150c18-14 40-14 58 0"/><path d="M126 122c14-11 32-11 46 0"/>
            <path d="M258 118c16-12 36-12 52 0"/>
          </g>
          <g fill="#285d4e" opacity=".85">
            <rect x="188" y="128" width="10" height="10"/><rect x="200" y="128" width="10" height="10"/>
            <rect x="188" y="140" width="10" height="10"/><rect x="200" y="140" width="10" height="10"/>
            <rect x="212" y="140" width="10" height="10"/>
          </g>
          <g fill="#c2603f">
            <rect x="300" y="252" width="7" height="20"/><rect x="308" y="250" width="26" height="14"/>
          </g>
          <g fill="#8b5247">
            <rect x="52" y="96" width="22" height="22" rx="3"/><rect x="57" y="101" width="12" height="12" fill="#f8faf4"/>
          </g>
        </svg>
        <figcaption class="figure-caption">一目标一山屿 · 地块随专注、打卡与记忆解锁</figcaption>
      </figure>
    </header>

    <main class="sections">
      <section class="band" aria-labelledby="mechanism-title">
        <div class="band-head">
          <h2 id="mechanism-title">它怎么运转</h2>
          <p>不是多一个聊天框,而是一台会把学习事务真正跑完的机器。</p>
        </div>
        <ol class="step-grid">
          <li v-for="(step, index) in steps" :key="step.title">
            <span class="step-index">{{ index + 1 }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.body }}</p>
            <code>{{ step.meta }}</code>
          </li>
        </ol>
      </section>

      <section class="band band-split" aria-labelledby="roles-title">
        <div class="band-head">
          <h2 id="roles-title">一支学习小队</h2>
          <p>五个角色各管一段,按请求自动路由,也可以互相委派。</p>
        </div>
        <ul class="role-list">
          <li v-for="role in roles" :key="role.name">
            <strong>{{ role.name }}</strong>
            <span>{{ role.desc }}</span>
          </li>
        </ul>
      </section>

      <section class="band band-split" aria-labelledby="stream-title">
        <div class="band-head">
          <h2 id="stream-title">过程完全可见</h2>
          <p>思考、工具调用与结果以 SSE 实时流式呈现,并持久化到运行记录,断线可补齐、随时可回放。</p>
        </div>
        <ol class="timeline">
          <li v-for="(entry, index) in timeline" :key="entry.kind" :style="{ '--order': index }">
            <span class="timeline-kind">{{ entry.kind }}</span>
            <p>{{ entry.text }}</p>
          </li>
        </ol>
      </section>

      <section class="band band-close" aria-labelledby="growth-title">
        <div>
          <h2 id="growth-title">地形即数据</h2>
          <p>每块解锁地块都能追溯回一次专注、一次打卡或一条记忆,群岛的高低就是你真实的投入结构。</p>
        </div>
        <p class="formula"><code>解锁地块 = 20 + ⌊专注分钟 ÷ 8⌋ + 打卡天数 × 3</code></p>
        <div class="actions">
          <RouterLink v-if="!auth.user" class="button primary" to="/register">创建第一个目标</RouterLink>
          <RouterLink v-else class="button primary" to="/world">回到我的群岛</RouterLink>
          <RouterLink class="button" to="/terrain-demo">先看山屿演示</RouterLink>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.landing{max-width:1180px;margin:0 auto;padding:clamp(2rem,5vw,4rem) clamp(1.25rem,5vw,4rem) clamp(3rem,6vw,5rem);color:#173b36}
.eyebrow{margin:0 0 1rem;color:#3f7a63;font-size:.78rem;font-weight:700;letter-spacing:.14em}
.hero{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:clamp(1.5rem,4vw,3.5rem);align-items:center}
.hero h1{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(2.1rem,5vw,3.6rem);line-height:1.25}
.lede{margin:1.1rem 0 0;max-width:34rem;color:#41605a;font-size:clamp(.95rem,1.4vw,1.05rem);line-height:1.85}
.actions{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.6rem}
.button{display:inline-flex;align-items:center;justify-content:center;min-height:2.75rem;padding:0 1.35rem;border:1px solid #285d4e;border-radius:8px;color:#285d4e;background:transparent;font:inherit;font-size:.88rem;font-weight:650;text-decoration:none}
.button.primary{color:#f8faf4;background:#285d4e}
.button:hover,.button:focus-visible{background:#1f4a3e;border-color:#1f4a3e;color:#f8faf4}
.note{margin:1rem 0 0;color:#41605a;font-size:.8rem}
.hero-figure{margin:0}
.hero-figure svg{display:block;width:100%;height:auto;border:1px solid #d4e2d4;border-radius:12px;background:#f1f6ee}
.figure-caption{margin:.7rem 0 0;color:#41605a;font-size:.76rem}
.sections{margin-top:clamp(2.5rem,6vw,4.5rem)}
.band{padding-top:clamp(2rem,4vw,3rem);border-top:1px solid #d6e3d6}
.band-split{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(1.5rem,4vw,3rem);align-items:start}
.band-head h2,.band-close h2{margin:0;font-family:"Noto Serif SC",Georgia,serif;font-weight:500;font-size:clamp(1.4rem,2.6vw,2rem)}
.band-head p,.band-close p{margin:.6rem 0 0;color:#41605a;line-height:1.8}
.step-grid{list-style:none;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin:1.75rem 0 0;padding:0}
.step-grid li{padding:1.25rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}
.step-index{display:inline-flex;align-items:center;justify-content:center;width:1.6rem;height:1.6rem;border-radius:999px;background:#e8efe6;color:#285d4e;font-size:.8rem;font-weight:700}
.step-grid h3{margin:.8rem 0 .5rem;font-size:1rem}
.step-grid p{margin:0;color:#41605a;font-size:.86rem;line-height:1.75}
.step-grid code{display:inline-block;margin-top:.9rem;padding:.2rem .5rem;border-radius:6px;background:#e8efe6;color:#2f6b58;font-size:.72rem}
.role-list{list-style:none;display:grid;gap:.6rem;margin:0;padding:0}
.role-list li{display:flex;gap:.9rem;padding:.85rem 1rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}
.role-list strong{flex-shrink:0;width:4rem;color:#285d4e;font-size:.88rem}
.role-list span{color:#41605a;font-size:.85rem;line-height:1.7}
.timeline{list-style:none;display:grid;gap:.6rem;margin:0;padding:0}
.timeline li{display:grid;grid-template-columns:4.2rem minmax(0,1fr);gap:.9rem;align-items:baseline;padding:.85rem 1rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4;animation:fade-in .5s ease-out both;animation-delay:calc(var(--order) * 140ms)}
.timeline-kind{color:#285d4e;font-size:.78rem;font-weight:700}
.timeline p{margin:0;color:#41605a;font-size:.85rem;line-height:1.7}
.band-close{display:grid;gap:1.2rem}
.formula{margin:0;padding:.9rem 1rem;border:1px solid #d4e2d4;border-radius:10px;background:#f8faf4}
.formula code{color:#2f6b58;font-size:.84rem}
@keyframes fade-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (max-width:960px){
  .hero,.band-split{grid-template-columns:minmax(0,1fr)}
  .step-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:620px){
  .step-grid{grid-template-columns:minmax(0,1fr)}
  .timeline li{grid-template-columns:minmax(0,1fr);gap:.35rem}
}
@media (prefers-reduced-motion:reduce){
  .timeline li{animation:none}
}
</style>
