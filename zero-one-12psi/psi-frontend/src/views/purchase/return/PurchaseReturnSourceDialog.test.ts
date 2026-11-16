import { describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import Dialog from './PurchaseReturnSourceDialog.vue'

describe('purchase return source facts', () => {
  it('distinguishes source allowance, draft reservations and current warehouse stock without reporting a save', async () => {
    const wrapper = mount(Dialog, { props: { modelValue: true, loading: false, error: '', source: { source: 'receipt', sourceNumber: 'QA-RECEIPT', sourceVersion: 'a'.repeat(64), supplier: 'supplier', supplierName: '原供货商', frame: 'org', user: 'actor', total: 150, actual: 169.5, items: [{ source: 'line', goodsName: '实际采购商品', unit: '箱', sourceQuantity: 2, returned: 0, reserved: .5, available: 1.5, stockQuantity: .8, price: 100, tpt: 169.5, serialRequired: true, availableSerials: ['ORIGINAL-SERIAL'] }] } }, global: { plugins: [ElementPlus], stubs: { ElDialog: { template: '<div><slot /><slot name="footer" /></div>' } } } })
    try { await flushPromises(); const text = wrapper.text(); expect(text).toContain('尚未生成退货单'); expect(text).toContain('草稿占用'); expect(text).toContain('当前库存'); expect(text).toContain('0.8'); expect(text).toContain('原供货商'); expect(text).toContain('ORIGINAL-SERIAL'); expect(text).toContain('169.5000'); expect(text).not.toContain('保存成功'); await wrapper.findAll('button').find(button => button.text() === '继续填写退货单')!.trigger('click'); expect(wrapper.emitted('continue')).toEqual([['receipt', 'a'.repeat(64)]]) } finally { wrapper.unmount() }
  })
})
