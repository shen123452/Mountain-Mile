import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { MotionPlugin } from '@vueuse/motion'
import router from './router'
import './styles/main.css'
import App from './App.vue'

createApp(App).use(createPinia()).use(router).use(MotionPlugin).mount('#app')
