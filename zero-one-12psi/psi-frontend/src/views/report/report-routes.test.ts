import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import ElementPlus from 'element-plus'
import HomeView from '@/views/HomeView.vue'
const routeModules = import.meta.glob<RouteRecordRaw[]>('@/router/main/*/index.ts', {
  eager: true,
  import: 'default'
})
function flattenRoutes(records: RouteRecordRaw[], prefix = ''): RouteRecordRaw[] {
  return records.flatMap((record) => {
    const path = (record.path.startsWith('/') ? record.path : `${prefix}/${record.path}`).replace(
      /^\//,
      ''
    )
    if (record.children?.length) return flattenRoutes(record.children, path)
    return record.component ? [{ ...record, path }] : []
  })
}
const routes = flattenRoutes(Object.values(routeModules).flat())

vi.mock('@/stores/user', async () => {
  const { defineStore } = await import('pinia')
  return {
    useUserStore: defineStore('report-test-user', {
      state: () => ({ user: null, menus: [], isLoaded: false })
    })
  }
})
vi.mock('@/components/ReIcon/src/hooks', () => ({ useRenderIcon: () => 'span' }))
vi.mock('@/plugins/http', async (original) => {
  const actual = await original<typeof import('@/plugins/http')>()
  const request = vi.fn((...args: unknown[]) => {
    const url = String(args[1] && typeof args[1] === 'string' ? args[1] : args[0])
    if (url.includes('getWarehouseNameList')) return Promise.resolve({ code: 10000, data: [] })
    // 有数据的付款表必须经过百分比和供应商字段映射，不能只验证空表。
    if (url.includes('procurement-payment-form'))
      return Promise.resolve({
        code: 10000,
        data: {
          rows: [
            {
              id: 'test-payment',
              type: '采购单',
              supplier: '回归测试供应商',
              total: 100,
              actual: 100,
              payment: 50,
              balance: 50,
              rate: '50%',
              nucleus: 1
            }
          ],
          total: 1
        }
      })
    return Promise.resolve({ code: 10000, data: { rows: [], total: 0 } })
  })
  const http = {
    get: request,
    post: request,
    put: request,
    patch: request,
    delete: request,
    request
  }
  return { ...actual, useHttp: () => http }
})

afterEach(() => {
  document.body.innerHTML = ''
  vi.unstubAllGlobals()
})

describe('all business routes', () => {
  for (const route of routes.filter((route) => route.component)) {
    it(`${route.path}: mounts, refreshes and leaves without render errors`, async () => {
      vi.stubGlobal(
        'ResizeObserver',
        class {
          observe() {}
          unobserve() {}
          disconnect() {}
        }
      )
      const errors: unknown[] = []
      const warnings: string[] = []
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [
          {
            path: '/',
            component: HomeView,
            children: [
              route,
              { path: 'next', component: defineComponent({ render: () => h('div', 'next-page') }) }
            ]
          }
        ]
      })
      await router.push('/' + route.path)
      const wrapper = mount(defineComponent({ template: '<router-view />' }), {
        attachTo: document.body,
        global: {
          plugins: [createPinia(), router, ElementPlus],
          config: {
            errorHandler: (error) => errors.push(error),
            warnHandler: (message) => {
              if (message.includes('not defined')) warnings.push(message)
            }
          }
        }
      })
      try {
        await flushPromises()
        expect(wrapper.find('.routerPage').exists()).toBe(true)
        expect(wrapper.get('.routerPage').text()).not.toContain('页面加载失败')
        expect(wrapper.get('.routerPage').text().length).toBeGreaterThan(0)
        if (route.path === 'report/purchase/payment') {
          expect(wrapper.get('.routerPage').text()).toContain('回归测试供应商')
          expect(wrapper.get('.routerPage').text()).toContain('部分核销')
        }
        const refresh = wrapper.findAll('button').find((button) => button.text().trim() === '刷新')
        if (refresh) {
          await refresh.trigger('click')
          await flushPromises()
        }
        expect(wrapper.get('.routerPage').text()).not.toContain('页面加载失败')
        await router.push('/next')
        await flushPromises()
        expect(wrapper.get('.routerPage').text()).toBe('next-page')
        expect(errors).toEqual([])
        expect(warnings).toEqual([])
      } finally {
        wrapper.unmount()
      }
    }, 20000)
  }
})
