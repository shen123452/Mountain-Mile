import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({ history: createWebHistory(), routes: [
  { path: '/', component: Home },
  { path: '/login', component: () => import('../views/Auth.vue') },
  { path: '/register', component: () => import('../views/Auth.vue') },
  { path: '/agent', component: () => import('../views/Placeholder.vue'), meta: { title: 'Agent 工作台', requiresAuth: true } },
  { path: '/world', component: () => import('../views/WorldDemo.vue'), meta: { title: '山屿地形演示', requiresAuth: true } },
] })

router.beforeEach(async to => {
  if (!to.meta.requiresAuth) return
  const auth = useAuthStore()
  await auth.restore()
  if (!auth.user) return { path: '/login', query: { next: to.fullPath } }
})
export default router
