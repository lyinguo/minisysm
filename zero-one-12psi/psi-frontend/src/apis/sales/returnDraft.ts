import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageDTO } from '@/apis/type'

export interface ReturnDraftDocument {
  version: string
  sourceVersion: string
  header: Record<string, any>
  items: Record<string, any>[]
}
export interface ReturnDraftInput {
  id?: string
  version?: string
  source: string
  sourceVersion: string
  number: string
  time: string
  money: number
  cost: number
  account: string
  data: string
  salesReturnOrderInfos: { id?: string; source: string; nums: number; serial?: string; data?: string }[]
}
export const returnDraftApi = {
  async document(id: string): Promise<ReturnDraftDocument> {
    const response = await useHttp().get('/sale/return/document/' + encodeURIComponent(id))
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '退货详情读取失败')
    if (response.data?.header?.id !== id || !/^[0-9a-f]{64}$/.test(response.data?.version || '')) throw new Error('退货详情数据不完整，请重新读取')
    return response.data
  },
  async list(params: Record<string, any>): Promise<PageDTO<Record<string, any>>> {
    const response = await useHttp().get('/sale/return/saleReturnList', params)
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '退货列表读取失败')
    if (!Array.isArray(response.data?.rows)) throw new Error('退货列表数据不完整，请重新查询')
    return response.data
  },
  async save(input: ReturnDraftInput): Promise<string> {
    const response = input.id ? await useHttp().put('/sale/return/updateSalesReturnOrder', input) : await useHttp().post('/sale/return/addSalesReturnOrder', input)
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '退货草稿未保存')
    if (typeof response.data !== 'string' || (input.id ? response.data !== input.id : !/^[0-9a-f]{32}$/.test(response.data))) throw new Error('服务未返回有效退货单编号，请先查询保存结果，不要重复新增')
    return response.data
  },
  async remove(id: string, version: string) {
    const response = await useHttp().delete('/sale/return/document/' + encodeURIComponent(id), { version })
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '退货草稿删除失败')
    if (response.data !== id) throw new Error('服务未确认指定草稿删除，请刷新列表核对')
  },
  async accounts(source: string, keyword: string, updating: boolean): Promise<Record<string, any>[]> {
    const response = await useHttp().get('/sale/return/accounts', { source, keyword, updating })
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '退款账户读取失败')
    if (!Array.isArray(response.data)) throw new Error('退款账户数据不完整，请重新查询')
    return response.data
  }
}
