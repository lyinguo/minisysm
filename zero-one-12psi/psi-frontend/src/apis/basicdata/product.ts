import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import type { PageResult, ApiResponse, PageQuery } from '@/apis/type'

const SUCCESS_CODE = 10000

export interface Product {
  id: string
  name: string
  py?: string
  number: string
  spec?: string
  category?: string
  brand?: string
  unit?: string
  buy?: number
  sell?: number
  code?: string
  location?: string
  stock?: number
  type?: number
  data?: string
  imgs?: string
  details?: string
  units?: string
  strategy?: string
  serial?: number
  batch?: number
  validity?: number
  protect?: number
  threshold?: number
  more?: string
  enabled?: number
  remark?: string
  goods_unit?: string
  specification_model?: string
  memo?: string
  term?: string
  price?: number
  costPrice?: number
  description?: string
  status?: number
  createTime?: string
  updateTime?: string
  categoryName?: string
}

export interface ProductQuery extends PageQuery {
  name?: string
  number?: string
  code?: string
  barcode?: string
  model?: string
  remark?: string
  brand?: string
  goods_unit?: string
  specification_model?: string
  category?: string
  type?: string | number
  memo?: string
  pageSize: number
  pageIndex: number
  py?: string
  spec?: string
  unit?: string
  buy?: number
  sell?: number
  location?: string
  stock?: number
  batch?: number
  validity?: number
  threshold?: number
}

export interface AddProductRequest {
  name: string
  number?: string
  py?: string
  spec?: string
  unit?: string
  buy?: number | string
  sell?: number | string
  location?: string
  type?: number | string
  category?: string | number
  brand?: string
  batch?: number | string
  validity?: number | string
  threshold?: number | string
  protect?: number | string
  data?: string
  img?: string
  enabled?: number
  remark?: string
  goods_unit?: string
  specification_model?: string
  memo?: string
  code?: string
  barcode?: string
  purchasePrice?: number | string
  salesPrice?: number | string
  [key: string]: any
}

export interface UploadFileRequest {
  filename?: string
  fileType: string
  saveType: string
  remark?: string
  file: File
}

function mapGoodsRow(row: any): Product {
  return {
    id: String(row.id ?? ''),
    name: row.name ?? '',
    py: row.py ?? '',
    number: row.number ?? '',
    code: row.number ?? row.code ?? '',
    spec: row.spec ?? '',
    specification_model: row.spec ?? '',
    model: row.spec,
    category: row.categoryName ?? row.category ?? '',
    brand: row.brand ?? '',
    unit: row.unit ?? '',
    goods_unit: row.unit ?? '',
    buy: Number(row.buy) || 0,
    sell: Number(row.sell) || 0,
    price: Number(row.sell) || 0,
    costPrice: Number(row.buy) || 0,
    barcode: row.code ?? '',
    location: row.location ?? '',
    stock: Number(row.stock) || 0,
    type: row.type ?? 0,
    data: row.data ?? '',
    remark: row.data ?? '',
    memo: row.data ?? '',
    enabled: row.enabled ?? 1
  } as Product
}

function formatProductPayload(data: any): Record<string, any> {
  const num = (v: any, d = 0) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : d
  }
  const name = String(data.name ?? '').trim()
  const number = String(data.number ?? data.code ?? '').trim()
  const category = String(data.category ?? '').trim()
  const unit = String(data.unit ?? data.goods_unit ?? '个').trim()
  if (!name) throw new Error('商品名称不能为空')
  if (!number) throw new Error('商品编号不能为空')
  if (!category) throw new Error('商品分类不能为空')
  if (!unit) throw new Error('商品单位不能为空')

  return {
    name,
    number,
    py: String(data.py ?? number ?? name).slice(0, 32),
    spec: data.spec ?? data.model ?? data.specification_model ?? '',
    category,
    brand: data.brand ?? '',
    unit,
    buy: num(data.buy ?? data.purchasePrice, 0),
    sell: num(data.sell ?? data.salesPrice, 0),
    code: data.barcode ?? data.code ?? '',
    location: data.location ?? '',
    stock: num(data.stock ?? data.stockThreshold, 0),
    type: num(data.type, 0),
    batch: num(data.batch ?? (data.batchProduct ? 1 : 0), 0),
    validity: num(data.validity ?? (data.validPeriod ? data.shelfLife : 0), 0),
    protect: num(data.protect ?? data.warningThreshold, 0),
    threshold: num(data.threshold ?? data.stockThreshold, 0),
    data: data.data ?? data.remark ?? data.memo ?? '',
    imgs: data.imgs ?? data.img ?? '[]',
    enabled: num(data.enabled, 1)
  }
}

export class ProductAPI {
  private static http = useHttp()

  private static ok<T>(body: any): ApiResponse<T> {
    if (body?.code === SUCCESS_CODE) {
      return { code: SUCCESS_CODE, message: body.message || 'success', data: body.data as T }
    }
    throw new Error(body?.message || '请求失败')
  }

  static async getProductList(query: ProductQuery): Promise<ApiResponse<PageResult<Product>>> {
    const params: Record<string, any> = {
      pageIndex: Number(query.pageIndex) || 1,
      pageSize: Number(query.pageSize) || 10
    }
    if (query.name?.trim()) params.name = query.name.trim()
    if (query.code?.trim()) params.number = query.code.trim()
    if (query.barcode?.trim()) params.code = query.barcode.trim()
    if (query.model?.trim()) params.spec = query.model.trim()
    if (query.brand?.trim()) params.brand = query.brand.trim()
    if (query.category) params.category = String(query.category)
    if (query.type !== undefined && query.type !== '') params.type = query.type
    try {
      const body = await this.http.get('/goods/query-list', params)
      const result = this.ok<PageResult<any>>(body)
      const rows = (result.data?.rows || []).map(mapGoodsRow)
      return {
        code: SUCCESS_CODE,
        message: result.message,
        data: {
          total: result.data?.total ?? rows.length,
          pageIndex: result.data?.pageIndex ?? params.pageIndex,
          pageSize: result.data?.pageSize ?? params.pageSize,
          pages: result.data?.pages ?? 1,
          rows
        }
      }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getProductDetail(id: string): Promise<ApiResponse<Product>> {
    if (!id?.trim()) throw new Error('商品ID不能为空')
    try {
      const body = await this.http.get('/goods/query-detail', { id: id.trim() })
      const result = this.ok<any>(body)
      return { code: SUCCESS_CODE, message: result.message, data: mapGoodsRow(result.data) }
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async addProduct(data: AddProductRequest): Promise<ApiResponse<string>> {
    try {
      const payload = formatProductPayload(data)
      const body = await this.http.post('/goods/add', payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async updateProduct(data: Product): Promise<ApiResponse<string>> {
    if (!data.id?.trim()) throw new Error('商品ID不能为空')
    try {
      const payload = { id: data.id.trim(), ...formatProductPayload(data) }
      const body = await this.http.put('/goods/update', payload)
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async deleteProduct(ids: string[]): Promise<ApiResponse<string>> {
    const safeIds = (Array.isArray(ids) ? ids : [ids]).map((id) => id?.trim()).filter(Boolean) as string[]
    if (!safeIds.length) throw new Error('商品ID不能为空')
    try {
      const body = await this.http.delete('/goods/remove', { data: safeIds })
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async getProductSpecs(): Promise<ApiResponse<Array<{ id: string; name: string; number: string }>>> {
    const list = await this.getProductList({ pageIndex: 1, pageSize: 1000 })
    return {
      code: SUCCESS_CODE,
      message: 'success',
      data: (list.data?.rows || []).map((item) => ({
        id: item.id,
        name: item.name,
        number: item.number
      }))
    }
  }

  static async uploadProductFile(fileData: UploadFileRequest): Promise<ApiResponse<string>> {
    const formData = new FormData()
    formData.append('file', fileData.file)
    try {
      const body = await this.http.post('/goods/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return this.ok<string>(body)
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }

  static async uploadProductFileAlt(fileData: UploadFileRequest): Promise<ApiResponse<string>> {
    return this.uploadProductFile(fileData)
  }

  static async uploadProductImage(file: File): Promise<ApiResponse<{ path: string }>> {
    throw new Error('商品图片上传接口尚未对接')
  }

  static async getProductStock(goodsId: string): Promise<ApiResponse<{ stock: number }>> {
    const detail = await this.getProductDetail(goodsId)
    return {
      code: SUCCESS_CODE,
      message: 'success',
      data: { stock: Number(detail.data?.stock) || 0 }
    }
  }

  static async validateProduct(data: { name?: string; number?: string; id?: string }): Promise<ApiResponse<boolean>> {
    const list = await this.getProductList({
      pageIndex: 1,
      pageSize: 10,
      code: data.number,
      name: data.name
    } as ProductQuery)
    const rows = list.data?.rows || []
    const duplicated = rows.some((row) => row.id !== data.id)
    return { code: SUCCESS_CODE, message: 'success', data: !duplicated }
  }

  static async exportProducts(query: ProductQuery): Promise<Blob> {
    try {
      const response = await this.http.post('/goods/export', {}, { responseType: 'blob' })
      return response as unknown as Blob
    } catch (error) {
      throw new Error(extractErrorMessage(error))
    }
  }
}
