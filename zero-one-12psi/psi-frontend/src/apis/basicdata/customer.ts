import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageResult } from '@/apis/type'
import type { ApiResponse } from '@/apis/type'
import type { PageQuery } from '@/apis/type'

const SUCCESS_CODE = 10000
const BASE_URL = '/basic_information/customer'

function mapCustomerRow(row: any) {
  if (!row || typeof row !== 'object') {
    return null
  }
  let contacts: any[] = []
  if (row.contacts) {
    try {
      contacts = typeof row.contacts === 'string' ? JSON.parse(row.contacts) : row.contacts
    } catch {
      contacts = []
    }
  }
  const main = Array.isArray(contacts) ? contacts.find((c) => c?.isMain) || contacts[0] : null
  return {
    id: String(row.id ?? ''),
    name: row.name ?? '',
    number: row.number ?? '',
    contact_person: main?.name ?? row.contact_person ?? '',
    telephone: main?.phone ?? row.telephone ?? '',
    email: row.email ?? '',
    address: row.address ?? main?.address ?? '',
    grade: row.grade ?? '',
    category: row.category ?? '',
    username: row.user ?? row.username ?? '',
    memo: row.data ?? row.memo ?? '',
    status: row.status ?? 1,
    createTime: row.createTime ?? '',
    updateTime: row.updateTime ?? ''
  }
}

function buildAddPayload(data: any) {
  const contacts = Array.isArray(data.contacts) ? data.contacts : []
  const name = String(data.name ?? '').trim()
  const number = String(data.number ?? data.code ?? '').trim()
  if (!name) throw new Error('客户名称为必填项')
  if (!number) throw new Error('客户编号为必填项')

  return {
    name,
    number,
    py: String(data.py ?? number ?? name).slice(0, 32),
    frame: (Array.isArray(data.organization) ? data.organization[0] : data.organization) || '0',
    user: (Array.isArray(data.ownerUser) ? data.ownerUser[0] : data.ownerUser ?? data.owner_user) || 'admin',
    category: data.category || '常规类别',
    grade: data.level || data.grade || '常规等级',
    bank: data.bank_name || data.bank || '',
    account: data.bank_account || data.bankAccount || '',
    tax: data.tax_number || data.taxNumber || '',
    data: data.memo || data.remark || '',
    contacts: JSON.stringify(contacts),
    balance: 0,
    more: '{}'
  }
}

export interface Customer {
  id: string
  name: string
  number: string
  contact_person: string
  telephone: string
  email?: string
  address?: string
  grade?: string
  category?: string
  username?: string
  memo?: string
  status?: number
  createTime?: string
  updateTime?: string
}

export interface CustomerQuery extends PageQuery {
  name?: string
  number?: string
  username?: string
  contact_person?: string
  category?: string
  grade?: string
  level?: string
  telephone?: string
  memo?: string
  page?: number
}

export interface AddCustomerRequest {
  name: string
  number: string
  contact_person: string
  telephone: string
  email?: string
  address?: string
  grade?: string
  category?: string
  username?: string
  memo?: string
}

export class CustomerAPI {
  private static http = useHttp()

  private static ok<T>(body: any): ApiResponse<T> {
    if (body?.code === SUCCESS_CODE) {
      return { code: SUCCESS_CODE, message: body.message || 'success', data: body.data as T }
    }
    throw new Error(body?.message || '请求失败')
  }

  static async getCustomerList(query: CustomerQuery): Promise<ApiResponse<PageResult<Customer>>> {
    const pageIndex = Number(query.page) || Number(query.pageIndex) || 1
    const pageSize = Number(query.pageSize) || 10
    const params: Record<string, any> = { pageIndex, pageSize }
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && !['page', 'pageIndex', 'pageSize'].includes(key)) {
        params[key === 'level' ? 'grade' : key] = value
      }
    })
    try {
      const body = await this.http.get(`${BASE_URL}/query-all`, params)
      const result = this.ok<PageResult<any>>(body)
      const rows = (result.data?.rows || []).map(mapCustomerRow).filter(Boolean) as Customer[]
      return {
        code: SUCCESS_CODE,
        message: result.message,
        data: {
          total: result.data?.total ?? rows.length,
          pageIndex: result.data?.pageIndex ?? pageIndex,
          pageSize: result.data?.pageSize ?? pageSize,
          pages: result.data?.pages ?? 1,
          rows
        }
      }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getCustomerDetail(id: string): Promise<ApiResponse<Customer>> {
    if (!id?.trim()) throw new Error('客户ID不能为空')
    try {
      const body = await this.http.get(`${BASE_URL}/query-one`, { id: id.trim() })
      const result = this.ok<any>(body)
      const customer = mapCustomerRow(result.data)
      if (!customer) throw new Error('客户不存在')
      return { code: SUCCESS_CODE, message: result.message, data: customer }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async addCustomer(data: any): Promise<ApiResponse<string>> {
    try {
      const payload = buildAddPayload(data)
      const body = await this.http.post(`${BASE_URL}/add-customer`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async updateCustomer(id: string, data: any): Promise<ApiResponse<string>> {
    if (!id?.trim()) throw new Error('客户ID不能为空')
    try {
      const payload = {
        id: id.trim(),
        ...buildAddPayload({ ...data, number: data.number ?? data.code, name: data.name }),
        contacts: JSON.stringify(Array.isArray(data.contacts) ? data.contacts : [])
      }
      const body = await this.http.put(`${BASE_URL}/update-customer`, payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async deleteCustomer(id: string): Promise<ApiResponse<string>> {
    return this.batchDeleteCustomer([id])
  }

  static async batchDeleteCustomer(ids: string[]): Promise<ApiResponse<string>> {
    const safeIds = (ids || []).map((id) => id?.trim()).filter(Boolean) as string[]
    if (!safeIds.length) throw new Error('客户ID不能为空')
    try {
      const body = await this.http.delete(`${BASE_URL}/delete-customer-list`, { data: safeIds })
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getCustomerNameList(): Promise<ApiResponse<Array<{ id: string; name: string }>>> {
    const list = await this.getCustomerList({ pageIndex: 1, pageSize: 1000 })
    return {
      code: SUCCESS_CODE,
      message: 'success',
      data: (list.data?.rows || []).map((item) => ({ id: item.id, name: item.name }))
    }
  }
}
