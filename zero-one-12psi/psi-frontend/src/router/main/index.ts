import type { RouteRecordRawArray } from '@/types/Route'
import type { RouteRecordRaw } from 'vue-router'

const homeRoute: RouteRecordRaw = {
  path: '/',
  name: 'Home',
  redirect: { name: 'Dashboard' },
  component: () => import('@/views/HomeView.vue'),
  children: [
    {
      path: 'dashboard',
      name: 'Dashboard',
      meta: {
        label: '首页',
        icon: 'mdi:view-dashboard'
      },
      component: () => import('@/views/dashboard/HomeDashboard.vue')
    }
  ]
}

const routes: RouteRecordRaw[] = [
  {
    path: '/home',
    redirect: '/dashboard'
  },
  homeRoute
]

// 读取子目录下面菜单设置为二级路由
const secondRouter = import.meta.glob<RouteRecordRawArray>('./**/index.ts', { eager: true })
for (const path in secondRouter) {
  homeRoute.children!.push(...secondRouter[path].default)
}

export default routes
