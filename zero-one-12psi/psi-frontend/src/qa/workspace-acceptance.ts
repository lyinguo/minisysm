import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIcons from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import '@/assets/main.css'
import '@/assets/lib.css'
import '@/assets/workspace.css'
import App from '@/App.vue'
import mainRoutes from '@/router/main'
import HttpPlugin from '@/plugins/http'
import icon from '@/plugins/icon'
import { useUserStore } from '@/stores/user'
import { IconifyIconOffline, IconifyIconOnline, FontIcon } from '@/components/ReIcon'

// This harness uses actual route components and isolated APIs. Menu fixtures grant
// test navigation only; they are not evidence of production authorization.
async function start() {
  const response = await fetch('/qa-session', { cache: 'no-store' })
  const session = await response.json()
  if (!session.token) throw new Error('Run QA login acceptance first')
  const app = createApp(App)
  app.use(createPinia())
  const router = createRouter({ history: createMemoryHistory(), routes: mainRoutes })
  const groups = [
    { text: '基础资料', paths: ['/product-manage', '/customer-manage', '/supplier-manage', '/warehouse-manage', '/fund-account'] },
    { text: '账号与组织', paths: ['/user-manage', '/user-role', '/organization-manage', '/staff-manage'] },
    { text: '采购与销售', paths: ['/purchase-booking', '/purchase-order', '/purchase-order-report', '/purchase-return', '/sales-booking', '/sales-order', '/sales-order-report', '/sales-return'] },
    { text: '库存与资金', paths: ['/inventory-query', '/other-inbound', '/other-outbound', '/transfer-order', '/receipt-order', '/payment-order', '/writeoff-order'] },
    { text: '报表查询', paths: ['/report/purchase/summary', '/report/purchase/payment', '/report/sales/summary', '/report/sales/profit'] },
    { text: '系统配置', paths: ['/sysmanage/import', '/sysmanage/dictionary', '/sysmanage/menu', '/system/summary'] }
  ]
  Object.assign(useUserStore(), {
    token: session.token, isLoaded: true, user: { username: '界面验收 · 隔离环境', avatar: '' },
    menus: groups.map((group, index) => ({ id: 'qa-group-' + index, text: group.text, icon: 'mdi:folder-outline', children: group.paths.filter(path => router.resolve(path).matched.length > 0).map(path => ({ id: path, href: path, text: String(router.resolve(path).meta.label || path), icon: 'mdi:circle-small', hideReport: true })) }))
  })
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })
  for (const [name, component] of Object.entries(ElementPlusIcons)) app.component(name, component)
  app.use(icon)
  app.use(HttpPlugin, { router })
  app.component('IconifyIconOffline', IconifyIconOffline)
  app.component('IconifyIconOnline', IconifyIconOnline)
  app.component('FontIcon', FontIcon)
  await router.push('/dashboard')
  await router.isReady()
  app.mount('#app')
}
void start()
