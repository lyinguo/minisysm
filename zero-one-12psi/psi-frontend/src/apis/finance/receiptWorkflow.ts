import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'

export interface ReceiptDocument { header: Record<string, any>; items: Record<string, any>[]; allocations: Record<string, any>[]; expenses?: Record<string, any>[]; invoices?: Record<string, any>[]; version: string }
export interface ReceiptAllocation { id: string; type: 'sell' | 'sre'; number: string; version: string; remaining: number; money: number }
export interface ReceiptPlan { receipt: string; version: string; cash: number; invoiceTotal: number; creditTotal: number; receivableNet: number; allocations: ReceiptAllocation[]; documents: ReceiptAllocation[] }
export interface ReceiptImportPlan { documents: { number: string; time: string; total: number }[]; references: { number: string; customerNumber: string; customer: string; accountNumber: string; account: string; money: number }[]; documentCount: number; lineCount: number; cash: number; version: string }
async function data<T>(promise: Promise<any>): Promise<T> { const result = await promise;if (result?.code !== 10000) throw new Error(extractErrorMessage(result));return result.data }
function version(value: string) { if (!/^[0-9a-f]{64}$/.test(value || '')) throw new Error('请重新读取并核对收款单') }
const base = '/fund/receipt'
export const receiptWorkflow = {
  async list(query: Record<string, unknown>) { const result = await data<{ rows: Record<string, any>[]; total: number }>(useHttp().get(base + '/documents', query));if (!Array.isArray(result?.rows)) throw new Error('收款列表不完整，请重新查询');return result },
  async document(id: string) { const result = await data<ReceiptDocument>(useHttp().get(base + '/document/' + encodeURIComponent(id)));if (result?.header?.id !== id || !Array.isArray(result.items) || !Array.isArray(result.allocations)) throw new Error('收款详情不完整，请重新读取');version(result.version);return result },
  async save(id: string | undefined, body: Record<string, unknown>) { if (id) version(String(body.version || ''));const result = await data<string>(id ? useHttp().put(base + '/document/' + encodeURIComponent(id), body) : useHttp().post(base, body));if (typeof result !== 'string' || !result || (id && result !== id)) throw new Error('未收到有效收款单ID，请先查询保存结果，不要重复新增');return result },
  async preview(id: string) { const result = await data<ReceiptPlan>(useHttp().get(base + '/settlement-preview', { id }));if (result?.receipt !== id || !Array.isArray(result.allocations) || !Array.isArray(result.documents)) throw new Error('收款结算方案不完整，请重新核对');version(result.version);return result },
  async settle(id: string, status: 0 | 1, reviewed: string, allocations?: ReceiptAllocation[]) { version(reviewed);const result = await data<number>(useHttp().post(base + '/settle', { id, status, version: reviewed, allocations }));if (result !== 0 && result !== 1) throw new Error('未收到有效入账结果，请重新读取收款单核实');return result },
  async remove(id: string, reviewed: string) { version(reviewed);const result = await data<string>(useHttp().delete(base + '/document/' + encodeURIComponent(id), { version: reviewed }));if (result !== id) throw new Error('服务未确认指定草稿删除，请重新查询') },
  options: (kind: 'customer' | 'account', keyword: string, document?: string) => data<{ rows: { id: string; name: string; number: string }[]; hasMore: boolean }>(useHttp().get(base + '/options', { kind, keyword, document })),
  template: () => useHttp().getFile(base + '/import-template', {}, { responseType: 'blob' }),
  async previewFile(file: File) { const result = await data<ReceiptImportPlan>(useHttp().postWithFile(base + '/import', { file }));if (!Array.isArray(result?.documents) || !Array.isArray(result.references) || !result.documentCount || result.documentCount !== result.documents.length || result.lineCount !== result.references.length) throw new Error('收款导入预览不完整，请重新选择文件核对');version(result.version);return result },
  async importFile(file: File, reviewed: string) { version(reviewed);const result = await data<{ ids: string[]; documentCount: number; lineCount: number; cash: number }>(useHttp().postWithFile(base + '/import', { file, version: reviewed }));if (!Array.isArray(result?.ids) || !result.ids.length || result.documentCount !== result.ids.length) throw new Error('未收到有效导入单据ID，请先查询导入结果');return result },
  export: (kind: 'simple' | 'detail', query: Record<string, unknown>) => useHttp().getFile(base + '/export/' + kind, query, { responseType: 'blob' })
}
