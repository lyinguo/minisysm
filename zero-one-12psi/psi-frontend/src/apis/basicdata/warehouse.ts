import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageResult, ApiResponse } from '@/apis/type'

const SUCCESS_CODE = 10000
const BASE_URL = '/basic_information/warehouse'

export interface Warehouse {
  id?: string
  name?: string
  number?: string
  frame?: string | string[]
  contacts?: string
  tel?: string
  add?: string
  data?: string
  contactPerson?: string
  contactPhone?: string
  address?: string
  deptName?: string
  remark?: string
}

export interface WarehouseQuery {
  pageIndex: number
  pageSize: number
  add?: string
  tel?: string
  contacts?: string
  data?: string
  number?: string
  name?: string
  contactPerson?: string
  contactPhone?: string
  address?: string
  deptName?: string
}

function formatWarehousePayload(data: Partial<Warehouse>): Warehouse {
  const frame = Array.isArray(data.frame) ? data.frame.join(',') : String(data.frame ?? '0')
  return {
    id: data.id,
    name: data.name?.trim(),
    number: data.number?.trim(),
    frame: frame.trim() || '0',
    contacts: data.contacts?.trim() || data.contactPerson?.trim(),
    tel: data.tel?.trim() || data.contactPhone?.trim(),
    add: data.add?.trim() || data.address?.trim(),
    data: data.data?.trim() || data.remark?.trim()
  }
}

export class WarehouseAPI {
  private static http = useHttp()

  private static ok<T>(body: any): ApiResponse<T> {
    if (body?.code === SUCCESS_CODE) {
      return { code: SUCCESS_CODE, message: body.message || 'success', data: body.data as T }
    }
    throw new Error(body?.message || '请求失败')
  }

  static async getWarehouseList(query: WarehouseQuery): Promise<ApiResponse<PageResult<Warehouse>>> {
    const params: Record<string, any> = {
      pageIndex: Number(query.pageIndex) || 1,
      pageSize: Number(query.pageSize) || 10
    }
    ;['name', 'number', 'contacts', 'tel', 'add', 'data'].forEach((key) => {
      const value = (query as any)[key]
      if (value !== undefined && value !== null && String(value).trim()) {
        params[key] = String(value).trim()
      }
    })
    try {
      const body = await this.http.get(`${BASE_URL}/query-list`, params)
      return this.ok<PageResult<Warehouse>>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getWarehouseDetail(id: string): Promise<ApiResponse<Warehouse>> {
    if (!id?.trim()) throw new Error('仓库ID不能为空')
    try {
      const body = await this.http.get(`${BASE_URL}/query-one`, { id: id.trim() })
      return this.ok<Warehouse>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async addWarehouse(data: Partial<Warehouse>): Promise<ApiResponse<string>> {
    const payload = formatWarehousePayload(data)
    if (!payload.name) throw new Error('仓库名称不能为空')
    if (!payload.number) throw new Error('仓库编号不能为空')
    try {
      const body = await this.http.post(`${BASE_URL}/add`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async updateWarehouse(id: string, data: Partial<Warehouse>): Promise<ApiResponse<string>> {
    if (!id?.trim()) throw new Error('仓库ID不能为空')
    const payload = formatWarehousePayload({ ...data, id: id.trim() })
    if (!payload.name) throw new Error('仓库名称不能为空')
    if (!payload.number) throw new Error('仓库编号不能为空')
    try {
      const body = await this.http.put(`${BASE_URL}/update`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async deleteWarehouse(id: string): Promise<ApiResponse<string>> {
    return this.batchDeleteWarehouse([id])
  }

  static async batchDeleteWarehouse(ids: string[]): Promise<ApiResponse<string>> {
    const safeIds = (ids || []).map((item) => item?.trim()).filter(Boolean) as string[]
    if (!safeIds.length) throw new Error('仓库ID不能为空')
    try {
      const body = await this.http.delete(`${BASE_URL}/delete`, { data: safeIds })
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }
}
