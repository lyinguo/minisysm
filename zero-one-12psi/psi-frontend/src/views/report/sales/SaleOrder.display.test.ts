import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import GoodSearch from '@/components/goodSearchConpoent/GoodSearchForm.vue'
import SaleOrder from './SaleOrder.vue'

const api = vi.hoisted(() => ({ query: vi.fn(), export: vi.fn() }))
vi.mock('@/apis/openapi-apifox/xiaoshoudingdangenzongbiao', () => ({
  salesOrderTrackingFormUsingGet: api.query,
  salesOrderTrackingFormOpenApiExportUsingGet: api.export
}))
vi.mock('@/plugins/http', async (original) => {
  const actual = await original<typeof import('@/plugins/http')>()
  const request = vi.fn().mockResolvedValue({ code: 10000, data: { rows: [], total: 0 } })
  return { ...actual, useHttp: () => ({ get: request, post: request, request }) }
})

const row = {
  frame: '测试组织甲', customerName: '测试客户甲', number: 'XS001',
  time: '2026-11-17', arrival: '2026-11-18', goodsName: '测试商品甲',
  warehouseName: '测试仓库甲', attr: '', unit: '件', price: 10,
  nums: 3, total: 30, unstockedQuantity: 3, unstockedAmount: 30, state: 0
}
function renderReport() {
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
  api.query.mockResolvedValue({ code: 10000, data: { rows: [
    row,
    { ...row, goodsName: '测试商品乙', warehouseName: '测试仓库乙', state: 2,
      unstockedQuantity: 0, unstockedAmount: 0 },
    { ...row, frame: '测试组织乙', customerName: '测试客户乙', number: 'XS002', state: 1,
      unstockedQuantity: 1, unstockedAmount: 10 }
  ], total: 3 } })
  return mount(SaleOrder, { attachTo: document.body, global: { plugins: [ElementPlus] } })
}

afterEach(() => {
  vi.clearAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('sales order follow-up display', () => {
  it('renders readable headings, document summaries and all outbound states', async () => {
    const wrapper = renderReport()
    try {
      await flushPromises()
      const text = wrapper.text()
      expect(text).not.toContain('\uFFFD')
      for (const label of ['导出', '刷新', '商品名称', '客户', '所属组织', '出库状态',
        '未出库数量', '未出库金额', '未出库(1)', '部分出库(1)', '已出库(1)', '2种商品', '2个仓库']) {
        expect(text).toContain(label)
      }
      expect(wrapper.find('input[placeholder="请选择客户"]').exists()).toBe(true)
      expect(wrapper.find('input[placeholder="请选择供应商"]').exists()).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('groups by product with readable customer, organization and order counts', async () => {
    const wrapper = renderReport()
    try {
      await flushPromises()
      wrapper.findComponent(GoodSearch).vm.$emit('search', { sortType: '商品排序' })
      await flushPromises()
      const text = wrapper.text()
      expect(text).not.toContain('\uFFFD')
      for (const label of ['2张单据', '2个组织', '2个客户', '未出库(1)', '部分出库(1)']) {
        expect(text).toContain(label)
      }
    } finally {
      wrapper.unmount()
    }
  })

  it('queries the selected customer and refreshes back to document sorting', async () => {
    const wrapper = renderReport()
    try {
      await flushPromises()
      const search = wrapper.findComponent(GoodSearch)
      search.vm.$emit('search', { customer: '测试客户乙', sortType: '商品排序' })
      await flushPromises()
      expect(api.query).toHaveBeenLastCalledWith({ params: expect.objectContaining({ customer: '测试客户乙' }) })
      const refresh = wrapper.findAll('button').find(button => button.text().trim() === '刷新')!
      await refresh.trigger('click')
      await flushPromises()
      expect(api.query.mock.lastCall?.[0].params).not.toHaveProperty('customer')
      expect(search.props('modelValue')).toMatchObject({ customer: '', sortType: '单据排序' })
      expect(wrapper.text()).toContain('2种商品')
      expect(wrapper.text()).not.toContain('\uFFFD')
      expect(search.props('config')?.customFields).toEqual([
        expect.objectContaining({ label: '排列方式', options: [
          { label: '单据排序', value: '单据排序' }, { label: '商品排序', value: '商品排序' }
        ] })
      ])
    } finally {
      wrapper.unmount()
    }
  })
})
