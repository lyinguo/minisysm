/*
 * 仓库管理-序列查询接口
 */
import { useHttp } from '@/plugins/http'
import type { PageResult, ApiResponse } from '@/apis/type'

const SUCCESS_CODE = 10000
const BASE_URL = '/j2-store/serial'
const http = useHttp()

export interface SerialQuery {
  pageIndex?: number
  pageSize?: number
  serialNumber?: string
  goodsName?: string
  goodsNumber?: string
  warehouseId?: string
  state?: number | null
}

export interface SerialRow {
  id: string
  serialNumber: string
  state: number
  stateLabel: string
  warehouseId: string
  warehouseName: string
  goodsId: string
  goodsName: string
  goodsNumber: string
  goodsSpec: string
  batchId?: string
  roomId?: string
}

export async function getSerialList(query: SerialQuery): Promise<ApiResponse<PageResult<SerialRow>>> {
  const params: Record<string, any> = {
    pageIndex: query.pageIndex || 1,
    pageSize: query.pageSize || 20
  }
  if (query.serialNumber) params.serialNumber = query.serialNumber
  if (query.goodsName) params.goodsName = query.goodsName
  if (query.goodsNumber) params.goodsNumber = query.goodsNumber
  if (query.warehouseId) params.warehouseId = query.warehouseId
  if (query.state !== undefined && query.state !== null && String(query.state) !== '') {
    params.state = query.state
  }
  const body = await http.get(`${BASE_URL}/list`, params, { showLoading: true })
  if (body?.code !== SUCCESS_CODE) {
    throw new Error(body?.message || '序列查询失败')
  }
  const data = body.data || {}
  const rows = (data.rows || []).map((row: any) => ({
    id: String(row.id ?? ''),
    serialNumber: row.serialNumber || row.number || '',
    state: Number(row.state ?? 0),
    stateLabel: row.stateLabel || '',
    warehouseId: String(row.warehouseId ?? row.warehouse ?? ''),
    warehouseName: row.warehouseName || '',
    goodsId: String(row.goodsId ?? row.goods ?? ''),
    goodsName: row.goodsName || '',
    goodsNumber: row.goodsNumber || '',
    goodsSpec: row.goodsSpec || '',
    batchId: row.batchId || row.batch || '',
    roomId: row.roomId || row.room || ''
  }))
  return {
    code: SUCCESS_CODE,
    message: body.message || 'success',
    data: {
      total: Number(data.total ?? rows.length),
      pageIndex: Number(data.pageIndex ?? params.pageIndex),
      pageSize: Number(data.pageSize ?? params.pageSize),
      pages: Number(data.pages ?? 1),
      rows
    }
  }
}
