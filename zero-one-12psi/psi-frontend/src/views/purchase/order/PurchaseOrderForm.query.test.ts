import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus, { ElDatePicker } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
const api = vi.hoisted(() => ({ getList: vi.fn() }))
vi.mock('@/apis/purchase/purchaseOrder', () => ({ PurchaseNoteAPI: api }))
vi.mock('./PurchaseOrderDetailDialog.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/operationbuttons/OperationButtons.vue', () => ({ default: { template: '<div />' } }))
import PurchaseOrderForm from './PurchaseOrderForm.vue'

function page(name = '真实采购供应商', total = 12) {
  return { code: 10000, data: { total, rows: [{ id: name, supplier: 'supplier-id', supplierName: name, frame: 'frame-id', frameName: '测试组织', number: name + '-单据', time: '2026-11-15 12:00:00', total: 100, actual: 100, buyMoney: 0, cost: 0, examine: 0, checkStatus: 0, nucleus: 0, cse: 3, invoice: 3 }] } }
}
function render() { return mount(PurchaseOrderForm, { global: { plugins: [createPinia(), [ElementPlus, { locale: zhCn }]] } }) }

describe('purchase document queries', () => {
  beforeEach(() => {
    api.getList.mockReset().mockResolvedValue(page())
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} })
  })
  it('uses server totals and displays page two without slicing it again', async () => {
    const wrapper = render()
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('共 12 条')
      api.getList.mockResolvedValueOnce(page('第二页供应商'))
      await wrapper.find('button.btn-next').trigger('click')
      await flushPromises()
      expect(api.getList).toHaveBeenLastCalledWith(expect.objectContaining({ pageIndex: 2 }))
      expect(wrapper.text()).toContain('第二页供应商')
    } finally { wrapper.unmount() }
  })
  it('queries the whole dataset with customer, dates and status, and refresh retains applied filters', async () => {
    const wrapper = render()
    try {
      await flushPromises()
      await wrapper.find('input[placeholder="输入供应商名称或编号"]').setValue(' 测试供应商 ')
      wrapper.findComponent(ElDatePicker).vm.$emit('update:modelValue', ['2026-11-15', '2026-11-15'])
      await wrapper.find('form.document-search').trigger('submit')
      await flushPromises()
      const expected = { supplier: '测试供应商', startTime: '2026-11-15', endTime: '2026-11-15', pageIndex: 1 }
      expect(api.getList).toHaveBeenLastCalledWith(expect.objectContaining(expected))
      await wrapper.find('input[placeholder="输入供应商名称或编号"]').setValue('尚未提交的新条件')
      await wrapper.findAll('button').find(button => button.text() === '刷新')!.trigger('click')
      await flushPromises()
      expect(api.getList).toHaveBeenLastCalledWith(expect.objectContaining(expected))
      await wrapper.findAll('button').find(button => button.text() === '重置')!.trigger('click')
      await flushPromises()
      expect(api.getList).toHaveBeenLastCalledWith(expect.objectContaining({ supplier: undefined, startTime: undefined, endTime: undefined }))
    } finally { wrapper.unmount() }
  })
  it('shows a retryable error rather than substituting demonstration documents', async () => {
    api.getList.mockRejectedValueOnce(new Error('服务暂时不可用'))
    const wrapper = render()
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('服务暂时不可用')
      expect(wrapper.text()).not.toContain('XSD251030')
      await wrapper.findAll('button').find(button => button.text() === '重新加载')!.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('真实采购供应商')
      expect(wrapper.find('.el-alert--error').exists()).toBe(false)
    } finally { wrapper.unmount() }
  })
  it('does not let a slower previous query overwrite the latest search', async () => {
    let resolveFirst!: (value: ReturnType<typeof page>) => void
    api.getList.mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve }))
    const wrapper = render()
    try {
      await flushPromises()
      api.getList.mockResolvedValueOnce(page('最新查询客户'))
      await wrapper.find('form.document-search').trigger('submit')
      await flushPromises()
      resolveFirst(page('过期查询客户'))
      await flushPromises()
      expect(wrapper.text()).toContain('最新查询客户')
      expect(wrapper.text()).not.toContain('过期查询客户')
    } finally { wrapper.unmount() }
  })
  it('returns to a valid page when the matching dataset shrinks', async () => {
    api.getList.mockResolvedValueOnce(page()).mockResolvedValue(page('剩余单据', 1))
    const wrapper = render()
    try {
      await flushPromises()
      await wrapper.find('button.btn-next').trigger('click')
      await flushPromises()
      expect(api.getList.mock.calls.map(call => call[0].pageIndex)).toEqual([1, 2, 1])
      expect(wrapper.text()).toContain('剩余单据')
    } finally { wrapper.unmount() }
  })
})
