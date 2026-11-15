import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import UserManage from '@/views/advancedSettings/user/UserManage.vue'
import HttpPlugin from '@/plugins/http'
import { useUserStore } from '@/stores/user'

async function start() {
  const response = await fetch('/qa-session', { cache: 'no-store' })
  if (!response.ok) throw new Error('QA session unavailable')
  const session = await response.json()
  if (!session.token) throw new Error('Run real QA login acceptance before opening this page')
  const app = createApp(UserManage)
  app.use(createPinia())
  useUserStore().token = session.token
  const router = createRouter({ history: createMemoryHistory(), routes: [] })
  app.use(router)
  app.use(HttpPlugin, { router })
  app.use(ElementPlus)
  app.mount('#app')
}
void start()
