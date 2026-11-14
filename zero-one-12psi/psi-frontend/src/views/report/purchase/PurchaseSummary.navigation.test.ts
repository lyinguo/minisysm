import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, shallowRef, type Component } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import PurchaseSummary from './PurchaseSummary.vue'
import HomeView from '@/views/HomeView.vue'

vi.mock('@/stores/user', async () => {
  const { defineStore } = await import('pinia')
  return { useUserStore: defineStore('navigation-test-user', {
    state: () => ({ user: null, menus: [], isLoaded: false })
  }) }
})
vi.mock('@/components/ReIcon/src/hooks', () => ({ useRenderIcon: () => 'span' }))

vi.mock('@/components/goodSearchConpoent/Warehouse.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/goodSearchConpoent/Supplier.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/goodSearchConpoent/PeopleList.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/goodSearchConpoent/UserList.vue', () => ({ default: { template: '<div />' } }))

vi.mock('@/apis/report/purchase/caigouhuizongbiao', () => ({
  purchaseOrderSummaryFormUsingGet: vi.fn().mockResolvedValue({ data: { rows: [], total: 0 } }),
  purchaseOrderSummaryFormOpenApiExportUsingGet: vi.fn()
}))

describe('purchase summary navigation', () => {
  it('unmounts the summary and renders the next page', async () => {
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
    const page = shallowRef<Component>(PurchaseSummary)
    const wrapper = mount(defineComponent({ setup: () => () => h(page.value) }), {
      attachTo: document.body,
      global: { plugins: [ElementPlus] }
    })
    await nextTick()
    page.value = defineComponent({ render: () => h('div', 'next-page') })
    await nextTick()
    expect(wrapper.text()).toBe('next-page')
    wrapper.unmount()
    vi.unstubAllGlobals()
  })

  it('switches real HomeView routes after opening the summary search popup', async () => {
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
    const errors: unknown[] = []
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: HomeView, children: [
        { path: 'report/purchase/summary', component: PurchaseSummary },
        { path: 'next', component: defineComponent({ render: () => h('div', 'next-page') }) }
      ] }]
    })
    await router.push('/report/purchase/summary')
    const wrapper = mount(defineComponent({ template: '<router-view />' }), {
      attachTo: document.body,
      global: { plugins: [createPinia(), router, ElementPlus], config: {
        errorHandler: error => { errors.push(error) }
      } }
    })
    await flushPromises()
    await wrapper.get('.search-btn').trigger('click')
    await flushPromises()
    await router.push('/next')
    await flushPromises()
    expect(wrapper.get('.routerPage').text()).toBe('next-page')
    await router.push('/report/purchase/summary')
    await flushPromises()
    expect(wrapper.find('.search-btn').exists()).toBe(true)
    await router.push('/next')
    await flushPromises()
    expect(wrapper.get('.routerPage').text()).toBe('next-page')
    expect(errors).toEqual([])
    wrapper.unmount()
    vi.unstubAllGlobals()
  })
})
