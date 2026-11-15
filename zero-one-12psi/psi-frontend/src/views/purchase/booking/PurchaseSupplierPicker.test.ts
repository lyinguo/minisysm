import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
const api = vi.hoisted(() => ({ getSupplierList: vi.fn() }))
vi.mock('@/apis/basicdata/supplier', () => ({ SupplierAPI: api }))
import PurchaseSupplierPicker from './PurchaseSupplierPicker.vue'
const page = (id = 'supplier-uuid', name = '真实供应商', total = 21) => ({ code: 10000, data: { rows: [{ id, name, number: 'SUP001' }], total } })
describe('purchase supplier selection', () => {
  beforeEach(() => { api.getSupplierList.mockReset().mockResolvedValue(page()) })
  function render() { return mount(PurchaseSupplierPicker, { attachTo: document.body, global: { plugins: [ElementPlus] } }) }
  function button(text: string) { return [...document.querySelectorAll('button')].find(item => item.textContent?.trim() === text)! }
  it('loads real pages and searches name and number separately instead of filtering the first 500', async () => {
    const wrapper = render()
    try {
      await wrapper.find('button').trigger('click'); await flushPromises()
      expect(api.getSupplierList).toHaveBeenLastCalledWith({ pageIndex: 1, pageSize: 10, name: undefined, code: undefined })
      document.querySelector<HTMLButtonElement>('.btn-next')!.click(); await flushPromises()
      expect(api.getSupplierList).toHaveBeenLastCalledWith(expect.objectContaining({ pageIndex: 2 }))
      const input = document.querySelector<HTMLInputElement>('input[aria-label="供应商编号"]')!
      input.value = ' SUP001 '; input.dispatchEvent(new Event('input', { bubbles: true }))
      button('查询供应商').click(); await flushPromises()
      expect(api.getSupplierList).toHaveBeenLastCalledWith({ pageIndex: 1, pageSize: 10, name: undefined, code: 'SUP001' })
      button('选用').click(); await flushPromises()
      expect(wrapper.emitted('select')?.[0]).toEqual([{ id: 'supplier-uuid', name: '真实供应商', code: 'SUP001' }])
    } finally { wrapper.unmount() }
  })
  it('keeps errors visible and supports retry without choosing a fabricated supplier', async () => {
    api.getSupplierList.mockRejectedValueOnce(new Error('供应商服务不可用')).mockResolvedValueOnce(page())
    const wrapper = render()
    try {
      await wrapper.find('button').trigger('click'); await flushPromises()
      expect(document.body.textContent).toContain('供应商服务不可用')
      expect(wrapper.emitted('select')).toBeUndefined()
      button('重试加载供应商').click(); await flushPromises()
      expect(document.body.textContent).toContain('真实供应商')
      expect(document.body.textContent).not.toContain('供应商服务不可用')
    } finally { wrapper.unmount() }
  })
})
