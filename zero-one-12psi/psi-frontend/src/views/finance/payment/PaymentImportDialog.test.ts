import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'
import { paymentTemplateBook, paymentTemplateHeaders } from '@/apis/finance/paymentTemplate'
const api = vi.hoisted(() => ({ importPreview: vi.fn(), importSave: vi.fn() }))
vi.mock('@/apis/finance/paymentWorkflow', () => ({ paymentWorkflow: api }))
import ImportDialog from './PaymentImportDialog.vue'
const version = 'b'.repeat(64)
function render() { return mount(ImportDialog, { props: { modelValue: true }, global: { plugins: [ElementPlus], stubs: { ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>' } } } }) }
async function upload(wrapper: ReturnType<typeof render>) {
  const book = paymentTemplateBook();book.Sheets['付款模板'] = XLSX.utils.aoa_to_sheet([paymentTemplateHeaders, ['QA001', '2026-11-15', 'S001', 'A001', '25', '', '', '']])
  const bytes = XLSX.write(book, { type: 'array', bookType: 'xlsx' }) as ArrayBuffer
  Object.defineProperty(wrapper.find('input[type="file"]').element, 'files', { configurable: true, value: [{ name: '付款.xlsx', size: bytes.byteLength, arrayBuffer: async () => bytes }] })
  await wrapper.find('input[type="file"]').trigger('change'); await flushPromises()
}
async function confirm(wrapper: ReturnType<typeof render>) { await wrapper.findAll('button').find(button => button.text().includes('确认导入'))!.trigger('click');await flushPromises() }
describe('付款模板明确预览及保存', () => {
  beforeEach(() => {
    vi.clearAllMocks();vi.restoreAllMocks()
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
    api.importPreview.mockResolvedValue({ version, documents: [], documentCount: 1, lineCount: 1, cash: 25 })
    api.importSave.mockResolvedValue({ ids: ['persisted-id'], documentCount: 1, lineCount: 1, cash: 25 })
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
  })
  it('读取真实模板字节后先预览，只有确认才提交冻结版本并报告实际ID', async () => {
    const wrapper = render()
    try {
      await upload(wrapper);expect(api.importPreview).toHaveBeenCalledOnce();expect(api.importSave).not.toHaveBeenCalled()
      expect(wrapper.text()).toContain('1 张付款草稿');await confirm(wrapper)
      expect(api.importSave).toHaveBeenCalledWith([expect.objectContaining({ number: 'QA001', supplierNumber: 'S001', accountNumber: 'A001', money: '25' })], version)
      expect(wrapper.emitted('saved')).toEqual([[['persisted-id']]])
      expect(wrapper.emitted('update:modelValue')).toEqual([[false]])
    } finally { wrapper.unmount() }
  })
  it('预览失败时显示实际原因且不能导入', async () => {
    api.importPreview.mockRejectedValue(new Error('供应商编号不存在'))
    const wrapper = render()
    try { await upload(wrapper);expect(wrapper.text()).toContain('供应商编号不存在');await confirm(wrapper);expect(api.importSave).not.toHaveBeenCalled();expect(wrapper.emitted('saved')).toBeUndefined() } finally { wrapper.unmount() }
  })
  it('导入结果未确认时保留预览并阻止再次提交，要求先查询结果', async () => {
    api.importSave.mockRejectedValue(new Error('连接中断'))
    const wrapper = render()
    try {
      await upload(wrapper);await confirm(wrapper);expect(wrapper.text()).toContain('先按单据编号查询结果')
      await confirm(wrapper);expect(api.importSave).toHaveBeenCalledOnce();expect(wrapper.emitted('saved')).toBeUndefined()
    } finally { wrapper.unmount() }
  })
})
