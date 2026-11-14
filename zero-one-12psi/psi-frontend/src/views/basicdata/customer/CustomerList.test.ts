import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'

const http = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import CustomerList from './CustomerList.vue'

describe('customer details', () => {
  it('opens a successful detail response and preserves fields and contacts', async () => {
    http.get.mockImplementation((url: string) => Promise.resolve({
      code: 10000, message: '操作成功',
      data: url.endsWith('query-all') ? { rows: [], total: 0 } : {
        id: 'customer-test', name: '回归测试客户', number: 'C001',
        grade: '会员', bank: '测试银行', account: '123', tax: 'tax-test',
        data: '测试备注', contacts: JSON.stringify([{ name: '测试联系人', phone: '123', isMain: true }])
      }
    }))
    const error = vi.spyOn(ElMessage, 'error')
    const wrapper = mount(CustomerList, { global: { plugins: [createPinia(), ElementPlus] } })
    try {
      await flushPromises()
      const state = (wrapper.vm as any).$.setupState
      await state.handleView({ id: 'customer-test' })
      await flushPromises()
      expect(state.dialogVisible).toBe(true)
      expect(state.customerForm).toMatchObject({
        name: '回归测试客户', code: 'C001', level: '会员',
        bank: '测试银行', bankAccount: '123', taxNumber: 'tax-test', remark: '测试备注'
      })
      expect(state.contactList).toEqual([expect.objectContaining({ name: '测试联系人', phone: '123' })])
      expect(error).not.toHaveBeenCalled()
      http.put.mockResolvedValueOnce({ code: 10000, data: 'customer-test' })
      await state.handleSave()
      expect(http.put).toHaveBeenCalledWith(expect.stringContaining('/update-customer'),
        expect.objectContaining({
          bank: '测试银行', account: '123', tax: 'tax-test', data: '测试备注',
          contacts: expect.stringContaining('测试联系人')
        }))
      expect(state.dialogVisible).toBe(false)
    } finally {
      wrapper.unmount()
      error.mockRestore()
    }
  })
})
