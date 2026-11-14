import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useTabStore } from '@/stores/tab'
import { useRouterIcons } from '@/stores/router-icons'
import type { RouteRecordRawArray } from '@/types/Route'

const routes: any[] = []

routes.push(
  {
    path: '/forbidden',
    name: 'Forbidden',
    component: () => import('../views/status/403.vue')
  },
  {
    path: '/error',
    name: 'Error',
    component: () => import('../views/status/500.vue')
  },
  {
    path: '/operation-test',
    name: 'operation-test',
    component: () => import('@/views/OperationPopTableTest.vue')
  }
)

const loginRouter = import.meta.glob<RouteRecordRawArray>('./login/index.ts', { eager: true })
for (const path in loginRouter) {
  routes.push(...loginRouter[path].default)
}

const mainRouter = import.meta.glob<RouteRecordRawArray>('./main/index.ts', { eager: true })
for (const path in mainRouter) {
  routes.push(...mainRouter[path].default)
}

const enableSample = import.meta.env.DEV || import.meta.env.VITE_ENABLE_SAMPLE === 'true'
if (enableSample) {
  const sampleRouter = import.meta.glob<RouteRecordRawArray>('./sample/index.ts', { eager: true })
  for (const path in sampleRouter) {
    routes.push(...sampleRouter[path].default)
  }
}

routes.push({
  path: '/:pathMatch(.*)*',
  name: 'NotFound',
  component: () => import('../views/status/404.vue')
})

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

const WHITE_ROUTE_NAMES = new Set(['Login', 'NotFound', 'Forbidden', 'Error'])

function isWhiteRoute(name: string | symbol | null | undefined) {
  return typeof name === 'string' && WHITE_ROUTE_NAMES.has(name)
}

router.beforeEach(async (to, from, next) => {
  const routerIconsStore = useRouterIcons()
  routerIconsStore.extractIconsFromRoutes(router.getRoutes())

  if (isWhiteRoute(to.name)) {
    const store = useUserStore()
    if (to.name === 'Login' && store.getToken) {
      next({ path: '/dashboard' })
      return
    }
    next()
    return
  }

  if (enableSample && to.path.includes('sample')) {
    next()
    return
  }

  const store = useUserStore()
  if (store.getToken) {
    if (!store.isLoaded) {
      try {
        await store.loadUser()
        await store.loadMenus()
        if (!store.getToken) { next({ name: 'Login' }); return }
        store.setLoaded(true)
      } catch (error) {
        if (!store.getToken) { next({ name: 'Login' }); return }
        next(error instanceof Error ? error : new Error('加载用户信息失败'))
        return
      }
    }
    next()
  } else {
    next({ name: 'Login' })
    ElMessage.warning('在未登录时，禁止访问其他页面！')
  }
})

router.afterEach((to) => {
  if (isWhiteRoute(to.name)) return
  if (enableSample && to.path.includes('sample')) return

  const tabstore = useTabStore()
  const label = typeof to.meta?.label === 'string' ? to.meta.label : undefined
  tabstore.syncRouteTab(to.path, label)
})

export default router
