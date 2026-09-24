<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isRegister = computed(() => route.path === '/register')
const name = ref('')
const email = ref('')
const password = ref('')
const pending = ref(false)
const error = ref('')

async function submit() {
  if (pending.value) return
  pending.value = true
  error.value = ''
  try {
    if (isRegister.value) await auth.register(name.value, email.value, password.value)
    else await auth.login(email.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//')
      ? route.query.next : '/agent'
    await router.replace(next)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '请求失败，请稍后重试'
  } finally { pending.value = false }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-story" aria-hidden="true">
      <div class="mountain mountain-back"></div><div class="mountain mountain-front"></div>
      <p>山程</p><strong>每一程，都有迹可循。</strong>
    </div>
    <div class="auth-panel">
      <div class="auth-form-wrap">
        <h1>{{ isRegister ? '开启你的山程' : '继续你的山程' }}</h1>
        <p class="auth-intro">{{ isRegister ? '创建账户，开始记录每一步学习投入。' : '欢迎回来，今天从哪里继续？' }}</p>
        <form @submit.prevent="submit">
          <label v-if="isRegister" for="auth-name">你的称呼</label>
          <input v-if="isRegister" id="auth-name" v-model.trim="name" autocomplete="name" required maxlength="80" />
          <label for="auth-email">邮箱</label>
          <input id="auth-email" v-model.trim="email" type="email" autocomplete="email" required maxlength="255" />
          <label for="auth-password">密码</label>
          <input id="auth-password" v-model="password" type="password" :autocomplete="isRegister ? 'new-password' : 'current-password'" required minlength="8" maxlength="128" :aria-describedby="isRegister ? 'password-hint' : undefined" />
          <p v-if="isRegister" id="password-hint" class="field-hint">至少 8 个字符</p>
          <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
          <button class="auth-submit" type="submit" :disabled="pending">{{ pending ? '请稍候…' : isRegister ? '创建账户' : '登录' }}</button>
        </form>
        <p class="auth-switch">{{ isRegister ? '已有账户？' : '还没有账户？' }} <RouterLink :to="isRegister ? '/login' : '/register'">{{ isRegister ? '去登录' : '创建账户' }}</RouterLink></p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.auth-page{display:grid;grid-template-columns:minmax(280px,42%) 1fr;min-height:calc(100vh - 72px);background:#f7f8f1}.auth-story{position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end;padding:4rem 4vw;color:#f3f2df;background:#164c45}.auth-story p,.auth-story strong{position:relative;z-index:1}.auth-story p{font-family:"Noto Serif SC",Georgia,serif;font-size:1rem;letter-spacing:.18em;margin:0 0 .7rem}.auth-story strong{font-family:"Noto Serif SC",Georgia,serif;font-size:clamp(1.8rem,3vw,3rem);font-weight:500;line-height:1.4}.mountain{position:absolute;width:120%;height:70%;left:-10%;bottom:10%;border-radius:50% 50% 0 0/65% 65% 0 0;transform:rotate(-10deg)}.mountain-back{background:#2d7164;bottom:24%;left:20%;transform:rotate(15deg)}.mountain-front{background:#206052}.auth-panel{display:grid;place-items:center;padding:3rem 6vw}.auth-form-wrap{width:min(100%,400px)}h1{font-family:"Noto Serif SC",Georgia,serif;font-size:clamp(2rem,3vw,2.8rem);font-weight:500;color:#153e36;margin:0}.auth-intro{color:#536d62;margin:.7rem 0 2.5rem}form{display:flex;flex-direction:column}label{font-weight:600;color:#244c41;font-size:.9rem;margin:1rem 0 .45rem}input{width:100%;height:46px;padding:0 .85rem;border:1px solid #9fb7a7;border-radius:8px;background:#fff;color:#173b36;font:inherit}input:focus-visible,.auth-submit:focus-visible,a:focus-visible{outline:3px solid #b58853;outline-offset:3px}.field-hint{font-size:.8rem;color:#536d62;margin:.4rem 0 0}.auth-error{margin:1rem 0 0;color:#9b342d;font-size:.9rem}.auth-submit{margin-top:1.5rem;height:48px;border:0;border-radius:8px;background:#1d5b4a;color:#fff;font:inherit;font-weight:700;cursor:pointer}.auth-submit:hover{background:#164b3c}.auth-submit:disabled{opacity:.65;cursor:wait}.auth-switch{color:#536d62;text-align:center;margin:1.5rem 0 0}.auth-switch a{color:#1d5b4a;font-weight:700;text-underline-offset:3px}@media(max-width:760px){.auth-page{grid-template-columns:1fr}.auth-story{min-height:190px;padding:2rem 7vw}.auth-story strong{font-size:1.5rem}.auth-panel{padding:2.5rem 7vw 4rem}.auth-intro{margin-bottom:1.5rem}}
</style>
