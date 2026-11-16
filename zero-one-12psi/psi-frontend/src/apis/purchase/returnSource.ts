import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'

export interface PurchaseReturnSource {
  source: string
  sourceNumber: string
  sourceVersion: string
  supplier: string
  supplierName: string
  frame: string
  user: string
  total: number
  actual: number
  items: Record<string, any>[]
}

export const purchaseReturnSourceApi = {
  async preview(id: string): Promise<PurchaseReturnSource> {
    const response = await useHttp().get('/j3-purchase/purchase-note/getBuildBre', { id })
    if (response.code !== 10000) throw new Error(extractErrorMessage(response) || '采购退货来源读取失败')
    const data = response.data
    if (data?.source !== id || !/^[0-9a-f]{64}$/.test(data?.sourceVersion || '') || !Array.isArray(data?.items) || !data.items.length || data.items.some((item: any) => !item.source || !Number.isFinite(Number(item.available)) || Number(item.available) <= 0)) throw new Error('采购退货来源信息不完整，请重新读取原采购单')
    return data
  }
}
