import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'

const SUCCESS_CODE = 10000

export interface TreeNode {
  id: string
  label: string
  children?: TreeNode[]
}

export interface CategoryTreeNode extends TreeNode {
  code: string
  level: number
  parentId: string
}

function mapFrameTree(nodes: any[]): TreeNode[] {
  return (nodes || []).map((node) => ({
    id: String(node.id ?? ''),
    label: node.name ?? node.label ?? '',
    children: node.children?.length ? mapFrameTree(node.children) : undefined
  }))
}

function mapCategoryTree(nodes: any[], level = 1, parentId = '0'): CategoryTreeNode[] {
  return (nodes || []).map((node) => ({
    id: String(node.id ?? ''),
    label: node.name ?? node.label ?? '',
    code: String(node.id ?? ''),
    level,
    parentId,
    children: node.children?.length
      ? mapCategoryTree(node.children, level + 1, String(node.id ?? ''))
      : undefined
  }))
}

export class CommonAPI {
  private static http = useHttp()

  private static assertSuccess(body: any) {
    if (body?.code !== SUCCESS_CODE) {
      throw new Error(body?.message || '请求失败')
    }
    return body.data
  }

  static async getOrgStructureTree(): Promise<TreeNode[]> {
    try {
      const body = await this.http.get('/basic_information/frame/getFrame')
      return mapFrameTree(this.assertSuccess(body) || [])
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getIncomeExpenseCategoryList(_params?: any): Promise<Array<{ id: string; name: string }>> {
    const body = await this.http.get('/j7-sysargs/iet/queryList', { pageIndex: 1, pageSize: 200, ..._params })
    const data = this.assertSuccess(body)
    return (Array.isArray(data?.rows) ? data.rows : []).map((row: any) => ({ id: String(row.id), name: String(row.name ?? '') }))
  }

  static async getProductCategoryTree(): Promise<CategoryTreeNode[]> {
    try {
      const body = await this.http.get('/goods/category-tree')
      return mapCategoryTree(this.assertSuccess(body) || [])
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getProductSelectList(params: any) {
    try {
      const body = await this.http.get('/goods/select-list', {
        pageIndex: params?.current || params?.pageIndex || 1,
        pageSize: params?.size || params?.pageSize || 10,
        name: params?.name,
        number: params?.code || params?.number
      })
      const data = this.assertSuccess(body)
      return {
        code: SUCCESS_CODE,
        message: 'success',
        data: {
          records: (data?.rows || []).map((row: any) => ({
            id: row.id,
            name: row.name,
            code: row.number
          })),
          total: data?.total ?? 0,
          size: data?.pageSize ?? 10,
          current: data?.pageIndex ?? 1,
          pages: data?.pages ?? 1
        }
      }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getUserList(_params?: any) {
    const body = await this.http.get('/c1-systemparameters/user/query-all', { pageIndex: 1, pageSize: 200, ..._params })
    this.assertSuccess(body)
    return body
  }

  static async getWarehouseNameList(): Promise<Array<{ id: string; name: string }>> {
    try {
      const body = await this.http.get('/basic_information/warehouse/getWarehouseNameList')
      const list = this.assertSuccess(body) || []
      return list.map((item: any) => ({
        id: String(item.id ?? ''),
        name: item.name ?? ''
      }))
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getPersonList(_params?: any) {
    const body = await this.http.get('/c1-systemparameters/personnel/query-by-list', { pageIndex: 1, pageSize: 200, ..._params })
    this.assertSuccess(body)
    return body
  }

  static async getSupplierList(params?: any) {
    try {
      const body = await this.http.get('/basic_information/supplier/querySupplierList', {
        pageIndex: params?.current || params?.pageIndex || 1,
        pageSize: params?.size || params?.pageSize || 100,
        name: params?.name
      })
      const data = this.assertSuccess(body)
      return {
        code: SUCCESS_CODE,
        message: 'success',
        data: {
          records: (data?.rows || []).map((row: any) => ({
            id: row.id,
            name: row.name,
            code: row.number
          })),
          total: data?.total ?? 0,
          size: data?.pageSize ?? 10,
          current: data?.pageIndex ?? 1,
          pages: data?.pages ?? 1
        }
      }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getCustomerList(params?: any) {
    try {
      const body = await this.http.get('/basic_information/customer/query-all', {
        pageIndex: params?.current || params?.pageIndex || 1,
        pageSize: params?.size || params?.pageSize || 100,
        name: params?.name
      })
      const data = this.assertSuccess(body)
      return {
        code: SUCCESS_CODE,
        message: 'success',
        data: {
          records: (data?.rows || []).map((row: any) => ({
            id: row.id,
            name: row.name,
            code: row.number
          })),
          total: data?.total ?? 0,
          size: data?.pageSize ?? 10,
          current: data?.pageIndex ?? 1,
          pages: data?.pages ?? 1
        }
      }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }
}
