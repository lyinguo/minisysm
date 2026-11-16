import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '@/assets/main.css'
import HttpPlugin from '@/plugins/http'
import { useUserStore } from '@/stores/user'
import UserRoleManage from '@/views/advancedSettings/userrole/UserRoleManage.vue'

async function start() {
  if (location.port !== '18030' || !['127.0.0.1', 'localhost'].includes(location.hostname)) throw new Error('QA role browser acceptance requires local port18030')
  const response = await fetch('/qa-session', { cache: 'no-store' })
  if (!response.ok) throw new Error('Prepare isolated QA session first')
  const session = await response.json()
  if (!session.token) throw new Error('Missing isolated QA session')
  localStorage.setItem('token', session.token); localStorage.removeItem('refreshToken')
  const app = createApp(UserRoleManage); app.use(createPinia()); Object.assign(useUserStore(), { token: session.token, isLoaded: true })
  const router = createRouter({ history: createWebHistory(), routes: [{ path: '/qa-role.html', component: UserRoleManage }] })
  app.use(router); app.use(ElementPlus, { locale: zhCn }); app.use(HttpPlugin, { router }); await router.isReady(); app.mount('#app')
}
void start()
