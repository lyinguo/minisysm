import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'
const bookingApi = vi.hoisted(() => ({ addPurchaseOrder: vi.fn() }))
vi.mock('@/components/ReIcon/src/hooks', () => ({ useRenderIcon: () => 'span' }))
vi.mock('@/apis/common/api', () => ({ CommonAPI: { getWarehouseNameList: vi.fn().mockResolvedValue([]) } }))
vi.mock('@/components/documentform/DocumentForm.vue', () => ({ default: { setup(_props: unknown, { expose }: { expose: (value: unknown) => void }) { expose({ formdata: { relatedPerson: 'people-uuid', arrivalDate: '2026-11-16', actualAmount: 226, documentCost: 200 } }); return {} }, template: '<div />' } }))
vi.mock('@/apis/purchase/PurchaseBooking/order', () => ({ PurchaseOrderAPI: bookingApi }))
vi.mock('@/apis/basicdata/supplier', () => ({ SupplierAPI: { getSupplierList: vi.fn().mockResolvedValue({ code: 10000, data: { rows: [], total: 0 } }) } }))
import PurchaseBook from './PurchaseBook.vue'
import PurchaseSupplierPicker from './PurchaseSupplierPicker.vue'
import { usePurchaseStore } from '@/stores/purchase'
import HomeView from '@/views/HomeView.vue'
describe('purchase booking supplier guidance', () => {
  it('submits real string identifiers and preserves draft state after successful save', async () => {
    bookingApi.addPurchaseOrder.mockReset().mockResolvedValue({ code: 10000, data: 'saved-order-uuid' })
    const pinia = createPinia()
    usePurchaseStore(pinia).savePurchaseBookData({ headerForm: { supplier: '实际供应商', supplierId: 'supplier-uuid', documentDate: '2026-11-15', documentNumber: 'QA-SAVE' }, isAudited: false, tableData: [{ productName: '实际商品', goodsId: 'goods-uuid', warehouseId: 'warehouse-uuid', unit: 'unit', price: 100, quantity: 2, amount: 200, taxRate: 13, taxAmount: 26, total: 226 }] })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
    await router.push('/'); await router.isReady()
    const wrapper = mount(PurchaseBook, { global: { plugins: [pinia, router, ElementPlus] } })
    try {
      await flushPromises()
      await wrapper.findAll('button').find(button => button.text() === '保存')!.trigger('click'); await flushPromises()
      expect(bookingApi.addPurchaseOrder).toHaveBeenCalledWith(expect.objectContaining({ supplier: 'supplier-uuid', people: 'people-uuid', purchaseOrderInfoDTOList: [expect.objectContaining({ goods: 'goods-uuid', warehouse: 'warehouse-uuid' })] }))
      expect(wrapper.find('.audit-stamp').exists()).toBe(false)
      expect(usePurchaseStore(pinia).getPurchaseBookData?.isAudited).toBe(false)
    } finally { wrapper.unmount() }
  })
  it('retains selection through the real workspace tab remount and asynchronous warehouse loading', async () => {
    const pinia = createPinia()
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: HomeView, children: [{ path: 'purchase-booking', component: PurchaseBook, meta: { label: '采购订单' } }, { path: 'supplier-manage', component: { template: '<div>供应商维护</div>' }, meta: { label: '供应商管理' } }] }] })
    await router.push('/purchase-booking'); await router.isReady()
    const wrapper = mount({ template: '<router-view />' }, { global: { plugins: [pinia, router, ElementPlus] } })
    try {
      await flushPromises()
      wrapper.findComponent(PurchaseSupplierPicker).vm.$emit('select', { id: 'workspace-supplier-uuid', name: '工作区返回保留', code: 'SUP003' }); await flushPromises()
      wrapper.findComponent(PurchaseSupplierPicker).vm.$emit('manage'); await flushPromises()
      await router.push('/purchase-booking'); await flushPromises()
      expect(wrapper.findComponent(PurchaseSupplierPicker).props('supplierId')).toBe('workspace-supplier-uuid')
      expect(usePurchaseStore(pinia).getPurchaseBookData?.headerForm.supplierId).toBe('workspace-supplier-uuid')
    } finally { wrapper.unmount() }
  })
  it('restores the selected UUID after navigating to supplier maintenance and back', async () => {
    const pinia = createPinia()
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-booking', component: PurchaseBook }, { path: '/supplier-manage', component: { template: '<div>供应商维护</div>' } }] })
    await router.push('/purchase-booking'); await router.isReady()
    const wrapper = mount({ template: '<router-view />' }, { global: { plugins: [pinia, router, ElementPlus] } })
    try {
      await flushPromises()
      wrapper.findComponent(PurchaseSupplierPicker).vm.$emit('select', { id: 'persisted-supplier-uuid', name: '返回后仍选中', code: 'SUP002' }); await flushPromises()
      wrapper.findComponent(PurchaseSupplierPicker).vm.$emit('manage'); await flushPromises()
      expect(wrapper.text()).toContain('供应商维护')
      await router.push('/purchase-booking'); await flushPromises()
      expect(wrapper.findComponent(PurchaseSupplierPicker).props('supplierId')).toBe('persisted-supplier-uuid')
      expect(wrapper.text()).toContain('返回后仍选中')
    } finally { wrapper.unmount() }
  })
  it('opens supplier selection on missing save and preserves actual UUID/name in its draft', async () => {
    const pinia = createPinia()
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
    await router.push('/'); await router.isReady()
    const wrapper = mount(PurchaseBook, { attachTo: document.body, global: { plugins: [pinia, router, ElementPlus] } })
    try {
      await flushPromises()
      await wrapper.findAll('button').find(button => button.text() === '保存')!.trigger('click'); await flushPromises()
      expect(document.body.textContent).toContain('选择采购订单供应商')
      const picker = wrapper.findComponent(PurchaseSupplierPicker)
      picker.vm.$emit('select', { id: 'actual-supplier-uuid', name: '实际选择供应商', code: 'SUP001' }); await flushPromises()
      expect(usePurchaseStore(pinia).getPurchaseBookData?.headerForm).toEqual(expect.objectContaining({ supplierId: 'actual-supplier-uuid', supplier: '实际选择供应商' }))
      expect(wrapper.text()).toContain('实际选择供应商')
      expect(picker.props('invalid')).toBe(false)
      picker.vm.$emit('clear'); await flushPromises()
      expect(usePurchaseStore(pinia).getPurchaseBookData?.headerForm.supplierId).toBe('')
    } finally { wrapper.unmount() }
  })
})
