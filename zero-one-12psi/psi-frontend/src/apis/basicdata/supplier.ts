import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageResult, ApiResponse } from '@/apis/type'
import type { PageQuery } from '@/apis/type'

const SUCCESS_CODE = 10000
const BASE_URL = '/basic_information/supplier'

export interface Supplier {
  id: string
  number: string
  code?: string
  name: string
  contacts: string
  address: string
  bank: string
  account: string
  taxNo: string
  type: string
  category: string
  status: number
  balance: number
  '应付余额'?: number
  remark: string
  createBy: string
  createTime: string
  updateBy: string
  updateTime: string
}

export interface SupplierQuery extends PageQuery {
  pageIndex: number
  pageSize: number
  code?: string
  name?: string
  bank?: string
  category?: string
  status?: number
  belongUser?: string
  remark?: string
}

export interface AddSupplierRequest {
  name: string
  contacts: string
  address: string
  bank: string
  account: string
  taxNo: string
  type: string
  category: string
  status: number
  remark: string
  code?: string
  number?: string
}

export interface UpdateSupplierRequest extends AddSupplierRequest {
  id: string
}

export interface SupplierExportQuery {
  code?: string
  name?: string
  bank?: string
  category?: string
  status?: number
}

function mapSupplierRow(row: any): Supplier {
  return {
    id: String(row.id ?? ''),
    number: row.number || row.code || '',
    code: row.number || row.code || '',
    name: row.name || '',
    category: row.category || '',
    balance: typeof row.balance === 'number' ? row.balance : Number(row.balance) || 0,
    contacts: row.contacts || '[]',
    address: row.address || '',
    bank: row.bank || '',
    account: row.account || '',
    taxNo: row.tax || row.taxNo || '',
    type: row.type || '',
    status: row.status ?? 1,
    remark: row.data || row.remark || '',
    createBy: '',
    createTime: '',
    updateBy: '',
    updateTime: ''
  }
}

function buildSupplierPayload(params: any, id?: string) {
  const number = String(params.code ?? params.number ?? '').trim()
  const name = String(params.name ?? '').trim()
  if (!name) throw new Error('供应商名称不能为空')
  if (!number) throw new Error('供应商编号不能为空')
  const frameRaw = Array.isArray(params.orgName)
    ? params.orgName[0]
    : params.orgName ?? params.frame
  const userRaw = params.belongUser ?? params.user
  const payload: Record<string, any> = {
    name,
    number,
    frame: frameRaw != null && String(frameRaw).trim() !== '' ? String(frameRaw) : '0',
    user: userRaw != null && String(userRaw).trim() !== '' ? String(userRaw) : 'admin',
    category: params.category || '常规类别',
    rate: typeof params.rate === 'number' ? params.rate : 0,
    bank: params.bank || '',
    account: params.account || '',
    tax: params.taxNo || params.tax || '',
    data: params.remark || params.data || '',
    contacts: params.contacts || '[]'
  }
  if (id) {
    payload.id = id
  }
  return payload
}

export class SupplierAPI {
  private static http = useHttp()

  private static ok<T>(body: any): ApiResponse<T> {
    if (body?.code === SUCCESS_CODE) {
      return { code: SUCCESS_CODE, message: body.message || 'success', data: body.data as T }
    }
    throw new Error(extractErrorMessage(body))
  }

  static async getSupplierList(query: SupplierQuery): Promise<ApiResponse<PageResult<Supplier>>> {
    const filteredQuery: Record<string, any> = {
      pageIndex: query.pageIndex || 1,
      pageSize: query.pageSize || 10
    }
    if (query.name) filteredQuery.name = query.name
    if (query.code) filteredQuery.number = query.code
    if (query.category) filteredQuery.category = query.category
    if (query.remark) filteredQuery.data = query.remark
    try {
      const result = await this.http.get(`${BASE_URL}/querySupplierList`, filteredQuery)
      if (result?.code === SUCCESS_CODE && result.data) {
        return {
          ...result,
          data: {
            ...result.data,
            rows: (result.data.rows || []).map(mapSupplierRow)
          }
        }
      }
      return result as ApiResponse<PageResult<Supplier>>
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getSupplierDetail(id: string): Promise<ApiResponse<Supplier>> {
    if (!id?.trim()) throw new Error('供应商ID不能为空')
    try {
      const body = await this.http.get(`${BASE_URL}/query-one`, { id: id.trim() })
      const result = this.ok<any>(body)
      return { code: SUCCESS_CODE, message: result.message, data: mapSupplierRow(result.data) }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async addSupplier(params: any): Promise<ApiResponse<string>> {
    try {
      const payload = buildSupplierPayload(params)
      const body = await this.http.post(`${BASE_URL}/add`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async updateSupplier(id: string, data: any): Promise<ApiResponse<string>> {
    if (!id?.trim()) throw new Error('供应商ID不能为空')
    try {
      const payload = buildSupplierPayload(data, id.trim())
      const body = await this.http.put(`${BASE_URL}/update`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async deleteSupplier(ids: string[]): Promise<ApiResponse<string>> {
    const safeIds = (ids || []).map((id) => id?.trim()).filter(Boolean) as string[]
    if (!safeIds.length) throw new Error('供应商ID不能为空')
    try {
      const body = await this.http.delete(`${BASE_URL}/delete`, { data: safeIds })
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async batchDeleteSupplier(ids: string[]): Promise<ApiResponse<string>> {
    return this.deleteSupplier(ids)
  }

  static async importSupplier(formData: FormData): Promise<ApiResponse<any>> {
    try {
      const body = await this.http.post(`${BASE_URL}/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return this.ok<any>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async downloadImportTemplate(): Promise<ApiResponse<string>> {
    return this.ok<string>(await this.http.get(`${BASE_URL}/template`))
  }

  static async exportSupplier(params?: SupplierExportQuery): Promise<any> {
    try {
      return await this.http.get(`${BASE_URL}/export`, params)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }
}
