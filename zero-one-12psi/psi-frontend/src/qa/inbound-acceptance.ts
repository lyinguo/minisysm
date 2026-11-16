import { createApp, h } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory, RouterView } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '@/assets/main.css'
import HttpPlugin from '@/plugins/http'
import { useUserStore } from '@/stores/user'
import mainRoutes from '@/router/main'
import InboundWorkspace from '@/views/warehouse/inbound/OtherInbound.vue'

// Dedicated isolated entry for exercising the same inbound workspace as the app.
async function start() {
  if (location.port !== '18030' || !['127.0.0.1', 'localhost'].includes(location.hostname))
    throw new Error('Inbound browser acceptance requires isolated port18030')
  const response = await fetch('/qa-session', { cache: 'no-store' })
  if (!response.ok) throw new Error('Prepare the real QA OAuth browser session first')
  const session = await response.json()
  if (!session.token) throw new Error('QA OAuth session unavailable')
  localStorage.setItem('token', session.token)
  localStorage.removeItem('refreshToken')
  const app = createApp({ render: () => h(RouterView) })
  app.use(createPinia())
  Object.assign(useUserStore(), { token: session.token, isLoaded: true })
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      ...mainRoutes,
      { path: '/qa-inbound.html', name: 'QaInboundWorkflow', component: InboundWorkspace }
    ]
  })
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })
  app.use(HttpPlugin, { router })
  await router.isReady()
  app.mount('#app')
}
void start()
