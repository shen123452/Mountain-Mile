<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AmbientSound from './components/AmbientSound.vue'

const router = useRouter()
const auth = useAuthStore()
onMounted(() => { void auth.restore() })

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
    <header class="topbar"><RouterLink class="brand" to="/">山程 <span>Mountain Mile</span></RouterLink><nav><RouterLink to="/world">群岛</RouterLink><RouterLink to="/agent">向导</RouterLink><button v-if="auth.user" type="button" @click="logout">退出登录</button><RouterLink v-else to="/login">登录</RouterLink></nav></header>
    <main><RouterView /></main>
    <AmbientSound />
  </div>
</template>
