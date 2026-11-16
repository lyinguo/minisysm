import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'

export interface PaymentDocument { header: Record<string, any>; items: Record<string, any>[]; allocations: Record<string, any>[]; expenses?: Record<string, any>[]; invoices?: Record<string, any>[]; version: string }
export interface PaymentAllocation { id: string; type: 'buy' | 'bre'; number: string; version: string; remaining: number; money: number }
export interface PaymentPlan { payment: string; version: string; cash: number; invoiceTotal: number; creditTotal: number; payableNet: number; allocations: PaymentAllocation[]; documents: PaymentAllocation[] }
export interface PaymentImportRow { number: string; date: string; supplierNumber: string; accountNumber: string; money: string | number; settle: string; remark: string; lineRemark: string }
export interface PaymentImportPlan { documents: Record<string, any>[]; documentCount: number; lineCount: number; cash: number; version: string }
async function data<T>(promise: Promise<any>): Promise<T> {
  const result = await promise
  if (result?.code !== 10000) throw new Error(extractErrorMessage(result))
  return result.data
}
function version(value: string) { if (!/^[0-9a-f]{64}$/.test(value || '')) throw new Error('请重新读取并核对付款单') }
export const paymentWorkflow = {
  async list(query: Record<string, unknown>) {
    const result = await data<{ rows: Record<string, any>[]; total: number }>(useHttp().get('/payment-order/documents', query))
    if (!Array.isArray(result?.rows)) throw new Error('付款列表不完整，请重新查询')
    return result
  },
  async document(id: string) {
    const result = await data<PaymentDocument>(useHttp().get('/payment-order/document/' + encodeURIComponent(id)))
    if (result?.header?.id !== id || !Array.isArray(result.items) || !Array.isArray(result.allocations)) throw new Error('付款详情不完整，请重新读取')
    version(result.version); return result
  },
  async save(id: string | undefined, body: Record<string, unknown>) {
    if (id) version(String(body.version || ''))
    const result = await data<string>(id ? useHttp().put('/payment-order/document/' + encodeURIComponent(id), body) : useHttp().post('/payment-order/add', body))
    if (typeof result !== 'string' || !result || (id && result !== id)) throw new Error('未收到有效付款单ID，请先查询保存结果，不要重复新增')
    return result
  },
  async preview(id: string) {
    const result = await data<PaymentPlan>(useHttp().get('/payment-order/settlement-preview', { id }))
    if (result?.payment !== id || !Array.isArray(result.allocations) || !Array.isArray(result.documents)) throw new Error('结算方案不完整，请重新核对')
    version(result.version); return result
  },
  async settle(id: string, status: 0 | 1, reviewed: string, allocations?: PaymentAllocation[]) {
    version(reviewed)
    const result = await data<number>(useHttp().post('/payment-order/settle', { id, status, version: reviewed, allocations }))
    if (result !== 0 && result !== 1) throw new Error('未收到有效入账结果，请重新读取单据核实')
    return result
  },
  async remove(id: string, reviewed: string) {
    version(reviewed)
    const result = await data<string>(useHttp().delete('/payment-order/document/' + encodeURIComponent(id), { version: reviewed }))
    if (result !== id) throw new Error('服务未确认指定草稿删除，请重新查询')
  },
  options: (kind: 'supplier' | 'account', keyword: string, document?: string) => data<{ rows: { id: string; name: string; number: string }[]; hasMore: boolean }>(useHttp().get('/payment-order/options', { kind, keyword, document })),
  importPreview: (rows: PaymentImportRow[]) => data<PaymentImportPlan>(useHttp().post('/payment-order/import-preview', { rows })),
  async importSave(rows: PaymentImportRow[], reviewed: string) {
    version(reviewed)
    const result = await data<{ ids: string[]; documentCount: number; lineCount: number; cash: number }>(useHttp().post('/payment-order/addmore', { rows, version: reviewed }))
    if (!Array.isArray(result?.ids) || !result.ids.length || result.documentCount !== result.ids.length) throw new Error('未收到有效导入单据ID，请先查询导入结果')
    return result
  },
  export: (kind: 'simple' | 'detail', query: Record<string, unknown>) => useHttp().getFile('/payment-order/export/' + kind, query, { responseType: 'blob' })
}
