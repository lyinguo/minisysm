import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageQuery } from '@/apis/type'

const SUCCESS_CODE = 10000

export interface FundsDTO {
  name: string
  number: string
  frame: number
  time: number
  balance: number
  data: string
}

export interface AccountDetailDTO {
  accountname: string
  accountnumber: string
  frame: string
  time: string
  initial: number
  balance: number
  data: string
  id: string
}

export interface AddAccountDTO {
  accountname: string
  accountnumber: string
  frame: string
  time: string
  initial: number
  balance: number
  data: string
}

export interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
}

export interface PageResponse<T> {
  pageIndex: number
  pageSize: number
  total: number
  pages: number
  rows: T[]
}

export interface AccountQuery extends PageQuery {
  name?: string
  number?: string
  data?: string
}

function mapAccountForm(data: Partial<AddAccountDTO>) {
  return {
    name: (data.accountname ?? (data as any).name ?? '').trim(),
    number: (data.accountnumber ?? (data as any).number ?? '').trim(),
    frame: (data.frame ?? '默认组织').trim(),
    time: data.time || new Date().toISOString().split('T')[0],
    initial: Number(data.initial ?? 0),
    data: (data.data ?? '').trim()
  }
}

export class AccountAPI {
  private static http = useHttp()

  static async getAccountList(params: AccountQuery) {
    const queryParams = {
      pageIndex: params.pageIndex || 1,
      pageSize: params.pageSize || 10,
      name: params.name || '',
      number: params.number || '',
      data: params.data || ''
    }
    try {
      const response = await this.http.get('/account/list', queryParams)
      if (response?.code === SUCCESS_CODE && response.data?.rows) {
        response.data.rows = response.data.rows.map((row: any) => ({
          ...row,
          id: String(row.id ?? ''),
          name: row.name || row.accountname || '',
          number: row.number || row.accountnumber || '',
          balance: typeof row.balance === 'number' ? row.balance : Number(row.balance) || 0
        }))
      }
      return response
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getAccountDetail(id: number | string) {
    const validId = String(id).trim()
    if (!validId) throw new Error('账户ID不能为空')
    try {
      return await this.http.get('/account/get', { id: validId })
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async addAccount(data: Partial<AddAccountDTO>) {
    const payload = mapAccountForm(data)
    if (!payload.name) throw new Error('账户名称不能为空')
    if (!payload.number) throw new Error('账户编号不能为空')
    try {
      return await this.http.post('/account/add', payload)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async updateAccount(id: number | string, data: Partial<AddAccountDTO>) {
    const validId = String(id).trim()
    if (!validId) throw new Error('账户ID不能为空')
    const payload = { id: validId, ...mapAccountForm(data) }
    try {
      return await this.http.put('/account/update', payload)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async deleteAccount(id: number | string) {
    const validId = String(id).trim()
    if (!validId) throw new Error('账户ID不能为空')
    try {
      return await this.http.delete('/account/delete', { id: validId })
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async batchDeleteAccount(ids: (number | string)[]) {
    const results = await Promise.all(ids.map((id) => this.deleteAccount(id)))
    const failed = results.find((item) => item?.code !== SUCCESS_CODE)
    if (failed) throw new Error(failed.message || '批量删除失败')
    return results[0]
  }
}
