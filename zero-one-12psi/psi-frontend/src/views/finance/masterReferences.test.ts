import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import Receipt from './receipt/receipt.vue'
import Payment from './payment/payment.vue'
import Transfer from './transfer/transfer.vue'

describe('finance master references', () => {
  it.each([
    ['收款', Receipt, 'Customer', 'customer', { id: 'customer-id', 客户编号: 'C001', 客户名称: '客户' }],
    ['付款', Payment, 'Supplier', 'supplier', { id: 'supplier-id', 供应商编号: 'S001', 供应商名称: '供应商' }],
    ['转账', Transfer, 'People', 'people', { id: 'person-id', 人员编号: 'P001', 人员名称: '人员' }]
  ] as const)('%s stores IDs rather than display numbers', async (_, component, selection, field, row) => {
    http.get.mockResolvedValue({ code: 10000, data: { rows: [], total: 0 } })
    const wrapper = mount(component, { global: { plugins: [createPinia(), ElementPlus] } })
    try {
      await flushPromises()
      const state = (wrapper.vm as any).$.setupState
      state['current' + selection] = [row]
      state['confirm' + selection]()
      expect(state.form[field]).toBe(row.id)
      state.currentPeople = [{ id: 'real-person', 人员编号: 'P002', 人员名称: '人员' }]
      state.confirmPeople()
      expect(state.form.people).toBe('real-person')
      const previous = state.form.people
      state.currentPeople = [{ id: 'one' }, { id: 'two' }]
      state.confirmPeople()
      expect(state.form.people).toBe(previous)
    } finally { wrapper.unmount() }
  })
})
