<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AmbientSound from './components/AmbientSound.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const menuOpen = ref(false)
onMounted(() => { void auth.restore() })
watch(() => route.fullPath, () => { menuOpen.value = false })

async function logout() {
  try {
    await auth.logout()
    await router.replace('/login')
  } catch {
    window.alert('退出失败，请检查网络后重试。')
  }
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="山程首页">
        <svg class="brand-home" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 9.5 12 3l9 6.5V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20Z"/><path d="M9.5 21.5v-7h5v7"/></svg>
        <strong>山程</strong><span>Mountain Mile</span>
      </RouterLink>
      <button class="menu-toggle" type="button" :aria-expanded="menuOpen" aria-controls="site-nav" :aria-label="menuOpen ? '关闭导航菜单' : '打开导航菜单'" @click="menuOpen = !menuOpen">
        <svg v-if="!menuOpen" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
      </button>
      <nav id="site-nav" class="site-nav" :class="{ 'site-nav--open': menuOpen }" aria-label="主导航">
        <div class="nav-primary">
          <RouterLink to="/world">群岛</RouterLink>
          <RouterLink to="/agent">向导</RouterLink>
          <RouterLink to="/chat">对话</RouterLink>
        </div>
        <span v-if="auth.user" class="nav-divider" aria-hidden="true"></span>
        <div v-if="auth.user" class="nav-secondary">
          <RouterLink to="/knowledge">资料</RouterLink>
          <RouterLink to="/observatory">观测台</RouterLink>
          <RouterLink to="/stats">山志</RouterLink>
        </div>
        <button v-if="auth.user" class="nav-session" type="button" @click="logout">退出登录</button>
        <RouterLink v-else class="nav-session" to="/login">登录</RouterLink>
      </nav>
    </header>
    <main><RouterView /></main>
    <AmbientSound />
  </div>
</template>

<style>
.topbar{position:relative;z-index:20;min-height:72px;padding:0 4.5vw}
.brand{display:inline-flex;align-items:center;gap:10px;min-height:40px;padding:0 12px;border-radius:8px;white-space:nowrap}
.brand svg{width:18px;height:18px;flex:none;fill:none;stroke:var(--accent);stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.brand strong{font-size:16px;letter-spacing:.02em}
.brand span{margin-left:0;font-size:12px;letter-spacing:0;color:var(--faint)}
.topbar .brand:hover{background:rgba(255,255,255,0.08)}
.topbar .brand.router-link-exact-active{background:rgba(143,214,176,0.14)}
.topbar .brand:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.site-nav,.nav-primary,.nav-secondary{display:flex;align-items:center}
.topbar nav.site-nav{gap:20px}
.nav-primary{gap:8px}
.nav-secondary{gap:6px}
.topbar .site-nav a,.topbar .site-nav button{display:inline-flex;align-items:center;min-height:38px;padding:0 11px;border:0;border-radius:6px;background:transparent;color:var(--muted);text-decoration:none;font:inherit;font-size:14px;white-space:nowrap;cursor:pointer}
.topbar .site-nav a:hover,.topbar .site-nav button:hover{background:rgba(255,255,255,0.08);color:var(--ink)}
.topbar .site-nav a.router-link-exact-active{background:rgba(143,214,176,0.14);color:var(--ink);font-weight:650}
.topbar .site-nav a:focus-visible,.topbar .site-nav button:focus-visible,.menu-toggle:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.nav-divider{width:1px;height:22px;background:var(--line)}
.site-nav .nav-session{margin-left:4px;color:var(--faint)}
.menu-toggle{display:none}
@media(max-width:900px){
  .topbar{padding:0 24px}
  .topbar nav.site-nav{gap:12px}
  .nav-primary,.nav-secondary{gap:2px}
  .topbar .site-nav a,.topbar .site-nav button{padding:0 8px;font-size:13px}
}
@media(max-width:760px){
  .topbar{min-height:64px;padding:0 18px}
  .menu-toggle{display:grid;place-items:center;width:40px;height:40px;margin-left:auto;border:1px solid var(--line);border-radius:6px;background:rgba(255,255,255,0.06);color:var(--ink);cursor:pointer}
  .menu-toggle svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round}
  .topbar nav.site-nav{display:none;position:absolute;top:calc(100% - 1px);left:0;right:0;align-items:stretch;gap:8px;padding:12px 18px 16px;border-bottom:1px solid var(--line);background:rgba(8,23,18,0.96);box-shadow:0 12px 24px rgba(0,0,0,0.45)}
  .topbar nav.site-nav.site-nav--open{display:flex;flex-direction:column}
  .nav-primary,.nav-secondary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px}
  .topbar .site-nav a,.topbar .site-nav button{justify-content:center;min-height:42px;padding:0 8px;font-size:14px}
  .nav-divider{width:100%;height:1px}
  .topbar .site-nav .nav-session{align-self:flex-end;min-height:36px;margin:0;padding:0 12px}
}
</style>
