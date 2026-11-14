import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import routes from '@/router/main/sysparams'
import warehouseReports from '@/router/main/report'
import DataVerification from './DataVerification.vue'

describe('legacy data verification menu', () => {
  it('resolves the real menu URL and navigates to an implemented reconciliation report', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [...routes, ...warehouseReports]
        .filter((route) => route.component)
        .map((route) => ({
          path: '/' + route.path,
          name: route.name,
          meta: route.meta,
          component:
            route.name === 'SystemSummary' ? DataVerification : { template: '<div>核对报表</div>' }
        }))
    })
    const resolved = router.resolve('/system/summary')
    expect(resolved.name).toBe('SystemSummary')
    expect(resolved.meta.label).toBe('数据核准')
    await router.push('/system/summary')
    const wrapper = mount(DataVerification, { global: { plugins: [router, ElementPlus] } })
    try {
      expect(wrapper.text()).toContain('全量成本重算尚未接入')
      await wrapper
        .findAll('button')
        .find((button) => button.text() === '查看库存余额')!
        .trigger('click')
      await flushPromises()
      expect(router.currentRoute.value.name).toBe('InventorySummary')
    } finally {
      wrapper.unmount()
    }
  })
})
