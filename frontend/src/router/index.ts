import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const router = createRouter({ history: createWebHistory(), routes: [
  { path: '/', component: Home },
  { path: '/login', component: () => import('../views/Placeholder.vue'), meta: { title: '登录' } },
  { path: '/agent', component: () => import('../views/Placeholder.vue'), meta: { title: 'Agent 工作台' } },
  { path: '/world', component: () => import('../views/Placeholder.vue'), meta: { title: '群岛总览' } },
] })
export default router
