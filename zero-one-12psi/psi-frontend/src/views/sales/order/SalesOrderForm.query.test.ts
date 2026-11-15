import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus, { ElDatePicker } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
const api = vi.hoisted(() => ({ getSaleList: vi.fn() }))
vi.mock('@/apis/sales/order', () => ({ saleOrderApi: api }))
vi.mock('./SalesOrderDetailDialog.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/operationbuttons/OperationButtons.vue', () => ({ default: { template: '<div />' } }))
import SalesOrderForm from './SalesOrderForm.vue'

function page(name = '真实销售客户', total = 12) {
  return { code: 10000, data: { total, rows: [{ id: name, customer: 'customer-id', customerName: name, frame: 'frame-id', frameName: '测试组织', number: name + '-单据', time: '2026-11-15 12:00:00', total: 100, actual: 100, money: 0, cost: 0, examine: 0, check: 0, nucleus: 0, cse: 3, invoice: 3 }] } }
}
function render() { return mount(SalesOrderForm, { global: { plugins: [createPinia(), [ElementPlus, { locale: zhCn }]] } }) }

describe('sales document queries', () => {
  beforeEach(() => {
    api.getSaleList.mockReset().mockResolvedValue(page())
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} })
  })
  it('uses server totals and displays page two without slicing it again', async () => {
    const wrapper = render()
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('共 12 条')
      api.getSaleList.mockResolvedValueOnce(page('第二页客户'))
      await wrapper.find('button.btn-next').trigger('click')
      await flushPromises()
      expect(api.getSaleList).toHaveBeenLastCalledWith(expect.objectContaining({ pageIndex: 2 }))
      expect(wrapper.text()).toContain('第二页客户')
    } finally { wrapper.unmount() }
  })
  it('queries the whole dataset with customer, dates and status, and refresh retains applied filters', async () => {
    const wrapper = render()
    try {
      await flushPromises()
      await wrapper.find('input[placeholder="输入客户名称或编号"]').setValue(' 测试客户 ')
      wrapper.findComponent(ElDatePicker).vm.$emit('update:modelValue', ['2026-11-15', '2026-11-15'])
      await wrapper.find('form.document-search').trigger('submit')
      await flushPromises()
      const expected = { customer: '测试客户', startTime: '2026-11-15T00:00:00', endTime: '2026-11-15T23:59:59.999999', pageIndex: 1 }
      expect(api.getSaleList).toHaveBeenLastCalledWith(expect.objectContaining(expected))
      await wrapper.find('input[placeholder="输入客户名称或编号"]').setValue('尚未提交的新条件')
      await wrapper.findAll('button').find(button => button.text() === '刷新')!.trigger('click')
      await flushPromises()
      expect(api.getSaleList).toHaveBeenLastCalledWith(expect.objectContaining(expected))
      await wrapper.findAll('button').find(button => button.text() === '重置')!.trigger('click')
      await flushPromises()
      expect(api.getSaleList).toHaveBeenLastCalledWith(expect.objectContaining({ customer: undefined, startTime: undefined, endTime: undefined }))
    } finally { wrapper.unmount() }
  })
  it('shows a retryable error rather than substituting demonstration documents', async () => {
    api.getSaleList.mockRejectedValueOnce(new Error('服务暂时不可用'))
    const wrapper = render()
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('服务暂时不可用')
      expect(wrapper.text()).not.toContain('XSD251030')
      await wrapper.findAll('button').find(button => button.text() === '重新加载')!.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('真实销售客户')
      expect(wrapper.find('.el-alert--error').exists()).toBe(false)
    } finally { wrapper.unmount() }
  })
  it('does not let a slower previous query overwrite the latest search', async () => {
    let resolveFirst!: (value: ReturnType<typeof page>) => void
    api.getSaleList.mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve }))
    const wrapper = render()
    try {
      await flushPromises()
      api.getSaleList.mockResolvedValueOnce(page('最新查询客户'))
      await wrapper.find('form.document-search').trigger('submit')
      await flushPromises()
      resolveFirst(page('过期查询客户'))
      await flushPromises()
      expect(wrapper.text()).toContain('最新查询客户')
      expect(wrapper.text()).not.toContain('过期查询客户')
    } finally { wrapper.unmount() }
  })
  it('returns to a valid page when the matching dataset shrinks', async () => {
    api.getSaleList.mockResolvedValueOnce(page()).mockResolvedValue(page('剩余单据', 1))
    const wrapper = render()
    try {
      await flushPromises()
      await wrapper.find('button.btn-next').trigger('click')
      await flushPromises()
      expect(api.getSaleList.mock.calls.map(call => call[0].pageIndex)).toEqual([1, 2, 1])
      expect(wrapper.text()).toContain('剩余单据')
    } finally { wrapper.unmount() }
  })
})
