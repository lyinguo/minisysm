import { useHttp, DataUpType } from '@/plugins/http'
import type { ApiResponse, PageDTO } from '@/apis/type'

// 定义一个功能模块基础url，方便替换
const currBaseUrl = '/j3-purchase/purchase-order'

// 采购订单详情项
export interface PurchaseOrderInfoDTO {
  /** 辅助属性 */
  attr?: string
  /** 备注信息 */
  data?: string
  /** 折扣率 */
  discount?: number
  /** 折扣额 */
  dsc?: number
  /** 所属商品ID */
  goods: string
  /** 数量 */
  nums: number
  /** 单价 */
  price: number
  /** 税额 */
  tat?: number
  /** 税率 */
  tax?: number
  /** 金额 */
  total: number
  /** 价税合计 */
  tpt: number
  /** 单位 */
  unit: string
  /** 仓库ID */
  warehouse: string
}

// 新增采购订单请求参数
export interface PurchaseOrderAddDTO {
  /** 实际金额 */
  actual: number
  /** 到货时间 */
  arrival: string
  /** 备注信息 */
  data?: string
  /** 单据附件 */
  file?: string
  /** 物流信息 */
  logistics?: string
  /** 单据编号 */
  number: string
  /** 关联人员ID */
  people: string
  /** 采购订单详情列表 */
  purchaseOrderInfoDTOList?: PurchaseOrderInfoDTO[]
  /** 关联单据ID */
  source?: string
  /** 供应商ID */
  supplier: string
  /** 单据时间 */
  time: string
  /** 单据金额 */
  total: number
}

// 修改采购订单请求参数
export interface PurchaseOrderUpdateDTO {
  version: string
  /** 实际金额 */
  actual: number
  /** 到货时间 */
  arrival: string
  /** 备注信息 */
  data?: string
  /** 单据附件 */
  file?: string
  /** 采购订单id编号 */
  id?: string
  /** 物流信息 */
  logistics?: string
  /** 单据编号 */
  number: string
  /** 关联人员ID */
  people: string
  /** 采购订单详情列表 */
  purchaseOrderInfoDTOList?: PurchaseOrderInfoDTO[]
  /** 关联单据ID */
  source?: string
  /** 供应商ID */
  supplier: string
  /** 单据时间 */
  time: string
  /** 单据金额 */
  total: number
}

// 采购订单列表查询请求参数
export interface PurchaseOrderListQuery {
  /** 到货结束时间 */
  arrivalEndTime?: string
  /** 到货开始时间 */
  arrivalStartTime?: string
  /** 备注信息 */
  data?: string
  /** 单据结束时间 */
  documentEndTime?: string
  /** 单据开始时间 */
  documentStartTime?: string
  /** 审核状态 */
  examine?: string
  /** 商品名称 */
  name?: string
  /** 单据编号 */
  number?: string
  /** 查询页码 */
  pageIndex?: number
  /** 查询条数 */
  pageSize?: number
  /** 关联人员 */
  people?: string
  /** 入库状态 */
  state?: string
  /** 供应商 */
  supplier?: string
  /** 制单人 */
  user?: string
}

// 采购订单列表数据对象
export interface PurchaseOrderListItem {
  version?: string
  /** 订单ID */
  id?: string | number
  frameName?: string
  supplierName?: string
  peopleName?: string
  userName?: string
  examineName?: string
  stateName?: string
  /** 实际金额 */
  actual: string | number
  /** 到货日期 */
  arrivalTime?: string
  /** 备注信息 */
  data?: string
  /** 单据时间 */
  documentTime?: string
  /** 审核状态 */
  examine?: string
  /** 所属组织 */
  frame?: string
  /** 商品名称 */
  goods?: string
  /** 单据编号 */
  number?: string
  /** 关联人员 */
  people?: string
  /** 入库状态 */
  state?: string
  /** 供应商 */
  supplier?: string
  /** 单据金额 */
  total: string | number
  /** 制单人 */
  user?: string
}

// 采购订单其他部分详情
export interface PurchaseOrderOtherDetailDTO {
  version?: string
  supplierName?: string
  peopleName?: string
  userName?: string
  frameName?: string
  examine?: number
  state?: number
  /** 实际金额 */
  actual?: string | number
  /** 到货日期 */
  arrivalTime?: string
  /** 备注信息 */
  data?: string
  /** 单据附件 */
  file?: string
  /** 物流信息 */
  logistics?: string
  /** 单据编号 */
  number?: string
  /** 关联人员 */
  people?: string
  /** 供应商 */
  supplier?: string
  /** 单据日期 */
  time?: string
  /** 单据金额 */
  total?: string | number
}

// 采购订单详情商品项
export interface PurchaseOrderDetailItem {
  discount?: string | number
  dsc?: string | number
  number?: string
  warehouseName?: string
  /** 金额 */
  amount?: string | number
  /** 辅助属性 */
  attr?: string
  /** 备注信息 */
  data?: string
  /** 商品编号 */
  goods?: string
  /** 入库数量 */
  handle?: string | number
  /** 商品名称 */
  name?: string
  /** 数量 */
  nums?: string | number
  /** 单价 */
  price?: string | number
  /** 采购订单其他部分详情 */
  purchaseOrderOtherDetailDTO?: PurchaseOrderOtherDetailDTO
  /** 规格型号 */
  spec?: string
  /** 税额 */
  tat?: string | number
  /** 税率 */
  tax?: string | number
  /** 价税合计 */
  tpt?: string | number
  /** 单位 */
  unit?: string
  /** 仓库 */
  warehouse?: string
}

// 采购订单详情响应（根据接口文档，data 可能是单个商品对象或商品数组）
export type PurchaseOrderDetailResponse = PurchaseOrderDetailItem | PurchaseOrderDetailItem[]

// 生成采购单其他部分数据对象
export interface PurchaseNoteOtherGenerateDataDTO {
  /** 结算账户 */
  account?: string
  /** 实际金额 */
  actual?: string
  /** 单据费用 */
  cost?: string
  /** 备注信息 */
  data?: string
  /** 单据附件 */
  file?: string
  /** 物流信息 */
  logistics?: string
  /** 实付金额 */
  money?: string
  /** 单据编号 */
  number?: string
  /** 关联人员 */
  people?: string
  /** 供应商 */
  supplier?: string
  /** 单据日期 */
  time?: string
  /** 单据金额 */
  total?: string
}

// 生成采购单数据对象
export interface PurchaseOrderGenerateDataDTO {
  /** 金额 */
  amount?: string
  /** 辅助属性 */
  attr?: string
  /** 批次号 */
  batch?: string
  /** 备注信息 */
  data?: string
  /** 商品编号 */
  goods?: string
  /** 商品名称 */
  name?: string
  /** 数量 */
  nums?: string
  /** 单价 */
  price?: string
  /** 生成采购单其他部分展示信息 */
  purchaseNoteOtherGenerateDataDTO?: PurchaseNoteOtherGenerateDataDTO
  /** 规格型号 */
  spec?: string
  /** 税额 */
  tat?: string
  /** 税率 */
  tax?: string
  /** 价税合计 */
  tpt?: string
  /** 单位 */
  unit?: string
  /** 仓库 */
  warehouse?: string
}


/**
 * 采购订单 API
 */
export class PurchaseOrderAPI {
  private static http = useHttp()
  private static orderError(error: any, fallback: string): Error {
    const payload = error?.response?.data ?? error?.data ?? error?.responseData
    const message = typeof payload?.data === 'string' && payload.data.trim()
      ? payload.data
      : typeof payload?.message === 'string' && payload.message.trim()
        ? payload.message
        : typeof error?.message === 'string' && error.message.trim() ? error.message : fallback
    return new Error(message)
  }

  static receivePreview(id:string) {
    return this.http.get<{header:Record<string,any>;items:Record<string,any>[];drafts:Array<{id:string;number:string}>}>(`${currBaseUrl}/receive-preview?id=${encodeURIComponent(id)}`)
  }
  static receiveOrder(data:{id:string;number:string;time:string;items:Array<{id:string;nums:number}>}) {
    return this.http.post<{id:string;number:string;source:string;lineCount:number;total:number;actual:number}>(`${currBaseUrl}/receive`,data,{upType:DataUpType.json})
  }

  static supply(goods: string) {
    return this.http.get<Array<{id:string;name:string;number:string;enabled:number}>>(`${currBaseUrl}/supply?goods=${encodeURIComponent(goods)}`)
  }
  static setSupply(goods: string, supplier: string, enabled: boolean) {
    return this.http.post<string>(`${currBaseUrl}/supply`, {goods, supplier, enabled}, {upType:DataUpType.json})
  }
  static split(data: {number:string;time:string;arrival:string;people?:string;data?:string;rows:Array<PurchaseOrderInfoDTO & {supplier:string}>}) {
    return this.http.post<Array<{id:string;number:string;supplier:string;lineCount:number}>>(`${currBaseUrl}/split`, data, {upType:DataUpType.json})
  }

  /**
   * 新增采购订单
   * 接口路径: /j3-purchase/purchase-order/add
   * 请求方法: POST
   */
  static async addPurchaseOrder(
    data: PurchaseOrderAddDTO
  ): Promise<ApiResponse<string>> {
    try {
      // 验证必填字段
      this.validateRequiredFields(data)
      
      // 清理空值，确保数据格式正确
      const cleanData = this.cleanRequestData(data)
      
      // 验证清理后的数据
      if (!cleanData.purchaseOrderInfoDTOList || cleanData.purchaseOrderInfoDTOList.length === 0) {
        throw new Error('采购订单详情列表不能为空，请确保所有行的商品ID和仓库ID都已填写')
      }
      
      // 调试日志：打印请求数据
      console.log('采购订单请求数据:', JSON.stringify(cleanData, null, 2))
      
      const result = await this.http.post<string>(
        `${currBaseUrl}/add`,
        cleanData,
        {
          upType: DataUpType.json,
          showLoading: true
        }
      )
      return result
    } catch (error: any) {
      console.error('新增采购订单失败:', error)
      // 打印详细的错误信息
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
        
        // 如果是服务器错误（9994），检查是否是数据库连接超时
        const responseData = error.response.data
        if (responseData?.code === 9994) {
          const errorData = typeof responseData.data === 'string' ? responseData.data : JSON.stringify(responseData.data)
          if (errorData && (
            errorData.includes('JDBC Connection') ||
            errorData.includes('wait_timeout') ||
            errorData.includes('CommunicationsException')
          )) {
            // 数据库连接超时错误已经在 http.ts 中处理，这里只需要重新抛出
            // 但可以添加额外的日志
            console.warn('检测到数据库连接超时，建议联系后端管理员检查数据库连接池配置')
          }
        }
      }
      throw error
    }
  }

  /**
   * 获取采购订单列表（条件+分页）
   * 接口路径: /j3-purchase/purchase-order/list
   * 请求方法: GET
   */
  static async getPurchaseOrderList(
    params: PurchaseOrderListQuery
  ): Promise<ApiResponse<PageDTO<PurchaseOrderListItem>>> {
    try {
      // 构建查询参数，移除 undefined 和空字符串
      const queryParams: Record<string, any> = {}
      
      Object.keys(params).forEach(key => {
        const value = (params as any)[key]
        // 保留数字 0、false 和有效值
        if (value !== undefined && value !== null && value !== '') {
          queryParams[key] = value
        }
      })

      // 确保分页参数存在
      if (!queryParams.pageIndex) {
        queryParams.pageIndex = 1
      }
      if (!queryParams.pageSize) {
        queryParams.pageSize = 10
      }

      const result = await this.http.get<PageDTO<PurchaseOrderListItem>>(
        `${currBaseUrl}/list`,
        queryParams,
        {
          showLoading: true
        }
      )
      return result
    } catch (error: any) {
      console.error('获取采购订单列表失败:', error)
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
      }
      throw error
    }
  }

  /**
   * 验证必填字段
   */
  private static validateRequiredFields(data: PurchaseOrderAddDTO): void {
    // 验证主对象必填字段
    if (!data.number || (typeof data.number === 'string' && data.number.trim() === '')) {
      throw new Error('单据编号不能为空')
    }
    if (!data.supplier || (typeof data.supplier === 'string' && data.supplier.trim() === '')) {
      throw new Error('供应商不能为空')
    }
    if (!data.time || (typeof data.time === 'string' && data.time.trim() === '')) {
      throw new Error('单据时间不能为空')
    }
    // arrival 可能是字符串或数字，需要先转换为字符串再验证
    const arrivalStr = data.arrival ? String(data.arrival).trim() : ''
    if (!arrivalStr) {
      throw new Error('到货时间不能为空')
    }

    // 验证详情列表
    if (!data.purchaseOrderInfoDTOList || data.purchaseOrderInfoDTOList.length === 0) {
      throw new Error('采购订单详情列表不能为空')
    }

    // 验证详情项必填字段
    data.purchaseOrderInfoDTOList.forEach((item, index) => {
      if (!item.goods || (typeof item.goods === 'string' && item.goods.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的商品ID不能为空`)
      }
      if (!item.warehouse || (typeof item.warehouse === 'string' && item.warehouse.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的仓库ID不能为空`)
      }
      if (!item.unit || (typeof item.unit === 'string' && item.unit.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的单位不能为空`)
      }
    })
  }

  /**
   * 清理请求数据，移除可选字段的空值
   * 过滤掉无效的详情项（goods 或 warehouse 为空的项）
   * 转换日期格式为 YYYY-MM-DD
   * 将 ID 字段转换为字符串格式
   */
  private static cleanRequestData(data: PurchaseOrderAddDTO): any {
    const cleaned: any = {}
    
    // 必填字段列表（即使为空也要保留）
    const requiredFields = ['number', 'supplier', 'people', 'time', 'arrival', 'actual', 'total']
    
    // ID 字段列表（需要转换为字符串）
    const idFields = ['supplier', 'people', 'source']
    const detailIdFields = ['goods', 'warehouse'] // warehouse 是字符串类型，需要转换为字符串
    
    // 处理主对象
    Object.keys(data).forEach(key => {
      const value = (data as any)[key]
      const isRequired = requiredFields.includes(key)
      
      // 处理日期格式转换
      if (key === 'arrival' && value) {
        cleaned[key] = this.formatDate(value)
      } else if (key === 'time' && value) {
        cleaned[key] = this.formatDate(value)
      } else if (idFields.includes(key) && value !== undefined && value !== null) {
        // ID 字段转换为字符串
        cleaned[key] = String(value)
      } else if (isRequired) {
        // 如果是必填字段，直接保留
        cleaned[key] = value
      } else if (key === 'purchaseOrderInfoDTOList' && Array.isArray(value)) {
        // 处理嵌套数组：过滤掉无效项（goods 或 warehouse 为空的项）
        const validItems = value
          .filter(item => {
            // 只保留 goods 和 warehouse 都不为空的项
            const goods = item.goods
            const warehouse = item.warehouse
            const goodsStr = goods !== undefined && goods !== null ? String(goods).trim() : ''
            // warehouse 是字符串类型，检查是否不为空
            const warehouseStr = warehouse !== undefined && warehouse !== null ? String(warehouse).trim() : ''
            return goodsStr !== '' && warehouseStr !== ''
          })
          .map(item => {
            const cleanedItem: any = {}
            Object.keys(item).forEach(itemKey => {
              const itemValue = (item as any)[itemKey]
              // 详情项中的必填字段
              const detailRequiredFields = ['goods', 'nums', 'price', 'total', 'tpt', 'unit', 'warehouse']
              const isDetailRequired = detailRequiredFields.includes(itemKey)
              
              // ID 字段转换为字符串
              if (detailIdFields.includes(itemKey) && itemValue !== undefined && itemValue !== null) {
                cleanedItem[itemKey] = String(itemValue)
              } else if (isDetailRequired || (itemValue !== undefined && itemValue !== null && itemValue !== '')) {
                // 必填字段保留，可选字段移除空值
                cleanedItem[itemKey] = itemValue
              } else if (itemValue === 0 || itemValue === false) {
                // 保留数字 0 和 false
                cleanedItem[itemKey] = itemValue
              }
            })
            return cleanedItem
          })
        
        // 如果过滤后还有有效项，才添加到 cleaned 中
        if (validItems.length > 0) {
          cleaned[key] = validItems
        }
      } else if (value !== undefined && value !== null && value !== '') {
        // 可选字段：移除空字符串和 null/undefined
        cleaned[key] = value
      } else if (value === 0 || value === false || (Array.isArray(value) && value.length === 0)) {
        // 保留数字 0、false、空数组
        cleaned[key] = value
      }
    })
    
    return cleaned
  }

  /**
   * 格式化日期为 YYYY-MM-DD 格式
   */
  private static formatDate(dateValue: string | Date): string {
    if (!dateValue) return ''
    
    try {
      // 如果是 ISO 格式字符串（如 2025-11-17T16:00:00.000Z）
      if (typeof dateValue === 'string') {
        // 如果已经是 YYYY-MM-DD 格式，直接返回
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
          return dateValue
        }
        
        // 如果是 ISO 格式，提取日期部分
        const date = new Date(dateValue)
        if (!isNaN(date.getTime())) {
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        }
      }
      
      // 如果是 Date 对象
      if (dateValue instanceof Date) {
        const year = dateValue.getFullYear()
        const month = String(dateValue.getMonth() + 1).padStart(2, '0')
        const day = String(dateValue.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }
      
      return String(dateValue)
    } catch (error) {
      console.warn('日期格式转换失败:', dateValue, error)
      return String(dateValue)
    }
  }

  /**
   * 批量审核/反审核采购订单
   * 接口路径: /j3-purchase/purchase-order/audit
   * 请求方法: PUT
   * @param ids 订单ID数组
   * @param type 操作类型：1=审核，0=反审核
   * @returns 响应数据
   */
  static async auditPurchaseOrders(
    ids: (number | string)[],
    type: 0 | 1,
    version?: string | Record<string,string>
  ): Promise<ApiResponse<string[]>> {
    try {
      if (!ids || ids.length === 0) {
        throw new Error('订单ID数组不能为空')
      }

      if (type === undefined || type === null) {
        throw new Error('操作类型不能为空')
      }

      const validIds = ids.map(id => {
        if (typeof id === 'number' && (!Number.isSafeInteger(id) || id <= 0)) throw new Error('请使用完整订单ID')
        const value = typeof id === 'string' ? id.trim() : typeof id === 'number' ? String(id) : ''
        if (!value || value === '0') throw new Error('订单ID不能为空')
        return value
      })
      if (new Set(validIds).size !== validIds.length || validIds.length > 200 || (type !== 0 && type !== 1)) throw new Error('请选择1到200张不同订单和有效审核操作')
      let snapshot: {version:string} | {versions:Record<string,string>}
      if (typeof version === 'string' && validIds.length === 1 && /^[0-9a-f]{64}$/.test(version)) snapshot={version}
      else if (version && typeof version === 'object' && !Array.isArray(version) && Object.keys(version).length===validIds.length && validIds.every(id=>Object.prototype.hasOwnProperty.call(version,id) && /^[0-9a-f]{64}$/.test(version[id]))) snapshot={versions:{...version}}
      else throw new Error('请刷新列表或重新打开详情，核对全部订单后提交完整版本')

      // 按照接口文档，参数名是 ids 和 type（type: 1=审核，0=反审核）
      const requestData = {
        ids: validIds,
        type: type,
        ...snapshot
      }

      const result = await this.http.put<string[]>(
        `${currBaseUrl}/audit`,
        requestData,
        {
          upType: DataUpType.json,
          showLoading: true
        }
      )
      return result
    } catch (error: any) {
      console.error('批量审核/反审核采购订单失败:', error)
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
      }
      throw this.orderError(error, '订单审核失败，请重新打开详情核对')
    }
  }

  static orderStatus(id: string | number) {
    return this.http.get<{id:string;frame:string;examine:number;state:number;version:string}>(`${currBaseUrl}/status?id=${encodeURIComponent(String(id))}`)
  }

  /**
   * 删除采购订单(支持批量)
   * 接口路径: /j3-purchase/purchase-order/delete
   * 请求方法: DELETE
   * @param ids 订单ID数组（接口要求为字符串数组）
   * @returns 响应数据
   */
  static async deletePurchaseOrders(
    ids: (number | string)[]
  ): Promise<ApiResponse<string>> {
    try {
      if (!ids || ids.length === 0) {
        throw new Error('订单ID数组不能为空')
      }

      // 过滤掉无效的ID并转换为字符串数组（接口要求）
      const validIds = ids
        .map(id => String(id).trim())
        .filter(id => id !== '' && id !== '0')

      if (validIds.length === 0) {
        throw new Error('订单ID数组中没有有效的订单ID')
      }

      // 按照接口文档，直接传递数组，使用 JSON 格式
      const result = await this.http.delete<string>(
        `${currBaseUrl}/delete`,
        validIds, // 直接传递数组，而不是包装在对象中
        {
          upType: DataUpType.json, // 使用 JSON 格式
          showLoading: true
        }
      )
      return result
    } catch (error: any) {
      console.error('删除采购订单失败:', error)
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
      }
      throw error
    }
  }

  /**
   * 获取指定采购订单详情
   * 接口路径: /j3-purchase/purchase-order/detail
   * 请求方法: GET
   * @param id 订单ID（字符串类型）
   * @returns 响应数据
   */
  static async getPurchaseOrderDetail(
    id: string | number
  ): Promise<ApiResponse<PurchaseOrderDetailResponse>> {
    try {
      if (id === undefined || id === null || id === '') {
        throw new Error('订单ID不能为空')
      }

      // 将 ID 转换为字符串
      const idStr = String(id)

      const result = await this.http.get<{version:string;header:Record<string,any>;items:Record<string,any>[]}>(`${currBaseUrl}/document?id=${encodeURIComponent(idStr)}`, undefined, {showLoading:true})
      if(result.code!==10000 || !result.data)return {code:result.code,message:result.message,data:undefined}
      const head=result.data.header
      const header={...head,arrivalTime:head.arrival,version:result.data.version}
      return {...result,data:result.data.items.map(item=>({...item,amount:item.total,purchaseOrderOtherDetailDTO:header}))}
    } catch (error: any) {
      console.error('获取采购订单详情失败:', error)
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
      }
      throw error
    }
  }

  /**
   * 获取生成采购单数据
   * 接口路径: /j3-purchase/purchase-order/generate-purchaseData
   * 请求方法: GET
   * @param id 订单ID
   * @returns 响应数据
   */
  static async getGeneratePurchaseData(
    id: string | number
  ): Promise<ApiResponse<PurchaseOrderGenerateDataDTO[]>> {
    try {
      if (id === undefined || id === null || id === '') {
        throw new Error('订单ID不能为空')
      }

      // 将 ID 转换为字符串
      const idStr = String(id)

      console.log('🔍 [获取生成采购单数据] 请求参数:', {
        id: idStr,
        idType: typeof id,
        url: `${currBaseUrl}/generate-purchaseData`
      })

      const result = await this.http.get<PurchaseOrderGenerateDataDTO[]>(
        `${currBaseUrl}/generate-purchaseData`,
        { id: idStr },
        {
          showLoading: true
        }
      )

      // 打印完整的响应数据
      console.log('✅ [获取生成采购单数据] 完整响应:', JSON.stringify(result, null, 2))
      console.log('📊 [获取生成采购单数据] 响应数据结构分析:', {
        code: result.code,
        message: result.message,
        hasData: !!result.data,
        dataType: Array.isArray(result.data) ? 'array' : typeof result.data,
        dataLength: Array.isArray(result.data) ? result.data.length : result.data ? 1 : 0,
        dataContent: result.data
      })

      // 如果是数组，打印数组详情
      if (Array.isArray(result.data)) {
        console.log(`📦 [获取生成采购单数据] 明细行数量: ${result.data.length}`)
        result.data.forEach((item, index) => {
          console.log(`  [明细行 ${index + 1}]:`, {
            goods: item.goods,
            name: item.name,
            nums: item.nums,
            price: item.price,
            warehouse: item.warehouse,
            hasOtherData: !!item.purchaseNoteOtherGenerateDataDTO
          })
        })
      } else if (result.data && typeof result.data === 'object') {
        const singleData = result.data as PurchaseOrderGenerateDataDTO
        console.log('📦 [获取生成采购单数据] 单个明细行:', {
          goods: singleData.goods,
          name: singleData.name,
          nums: singleData.nums,
          price: singleData.price,
          warehouse: singleData.warehouse,
          hasOtherData: !!singleData.purchaseNoteOtherGenerateDataDTO
        })
      } else {
        console.warn('⚠️ [获取生成采购单数据] 响应数据为空!')
      }

      return result
    } catch (error: any) {
      console.error('❌ [获取生成采购单数据] 请求失败:', error)
      if (error.response) {
        console.error('📥 [获取生成采购单数据] 错误响应数据:', JSON.stringify(error.response.data, null, 2))
        console.error('📥 [获取生成采购单数据] 错误响应状态:', error.response.status)
        console.error('📥 [获取生成采购单数据] 错误响应头:', error.response.headers)
      }
      if (error.message) {
        console.error('📥 [获取生成采购单数据] 错误消息:', error.message)
      }
      throw error
    }
  }

  /**
   * 修改采购订单
   * 接口路径: /j3-purchase/purchase-order/update
   * 请求方法: PUT
   * @param data 更新订单数据
   * @returns 响应数据
   */
  static async updatePurchaseOrder(
    data: PurchaseOrderUpdateDTO
  ): Promise<ApiResponse<string>> {
    try {
      // 验证必填字段
      this.validateUpdateRequiredFields(data)
      
      // 清理空值，确保数据格式正确
      const cleanData = this.cleanUpdateRequestData(data)
      
      // 验证清理后的数据
      if (!cleanData.purchaseOrderInfoDTOList || cleanData.purchaseOrderInfoDTOList.length === 0) {
        throw new Error('采购订单详情列表不能为空，请确保所有行的商品ID和仓库ID都已填写')
      }
      
      const result = await this.http.put<string>(
        `${currBaseUrl}/update`,
        cleanData,
        {
          upType: DataUpType.json,
          showLoading: true
        }
      )
      return result
    } catch (error: any) {
      console.error('修改采购订单失败:', error)
      // 打印详细的错误信息
      if (error.response) {
        console.error('响应数据:', error.response.data)
        console.error('响应状态:', error.response.status)
      }
      throw this.orderError(error, '订单修改失败，请重新打开详情核对')
    }
  }

  /**
   * 验证更新必填字段
   */
  private static validateUpdateRequiredFields(data: PurchaseOrderUpdateDTO): void {
    if (!/^[0-9a-f]{64}$/.test(data.version || '')) throw new Error('请重新打开订单取得当前版本后再保存')
    // 验证主对象必填字段
    if (!data.number || (typeof data.number === 'string' && data.number.trim() === '')) {
      throw new Error('单据编号不能为空')
    }
    if (!data.supplier || (typeof data.supplier === 'string' && data.supplier.trim() === '')) {
      throw new Error('供应商不能为空')
    }
    if (!data.time || (typeof data.time === 'string' && data.time.trim() === '')) {
      throw new Error('单据时间不能为空')
    }
    // arrival 可能是字符串或数字，需要先转换为字符串再验证
    const arrivalStr = data.arrival ? String(data.arrival).trim() : ''
    if (!arrivalStr) {
      throw new Error('到货时间不能为空')
    }

    // 验证详情列表
    if (!data.purchaseOrderInfoDTOList || data.purchaseOrderInfoDTOList.length === 0) {
      throw new Error('采购订单详情列表不能为空')
    }

    // 验证详情项必填字段
    data.purchaseOrderInfoDTOList.forEach((item, index) => {
      if (!item.goods || (typeof item.goods === 'string' && item.goods.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的商品ID不能为空`)
      }
      if (!item.warehouse || (typeof item.warehouse === 'string' && item.warehouse.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的仓库ID不能为空`)
      }
      if (!item.unit || (typeof item.unit === 'string' && item.unit.trim() === '')) {
        throw new Error(`第 ${index + 1} 行的单位不能为空`)
      }
    })
  }

  /**
   * 清理更新请求数据，移除可选字段的空值
   * 过滤掉无效的详情项（goods 或 warehouse 为空的项）
   * 转换日期格式为 YYYY-MM-DD
   * 将 ID 字段转换为字符串格式
   */
  private static cleanUpdateRequestData(data: PurchaseOrderUpdateDTO): any {
    const cleaned: any = {}
    
    // 必填字段列表（即使为空也要保留）
    // Empty editable text means clear it, rather than silently retain the old value.
    const requiredFields = ['number', 'supplier', 'people', 'time', 'arrival', 'actual', 'total', 'data', 'logistics', 'file']
    
    // ID 字段列表（需要转换为字符串）
    const idFields = ['supplier', 'people', 'source', 'id']
    const detailIdFields = ['goods', 'warehouse'] // warehouse 是字符串类型，需要转换为字符串
    
    // 处理主对象
    Object.keys(data).forEach(key => {
      const value = (data as any)[key]
      const isRequired = requiredFields.includes(key)
      
      // 处理日期格式转换
      if (key === 'arrival' && value) {
        cleaned[key] = this.formatDate(value)
      } else if (key === 'time' && value) {
        cleaned[key] = this.formatDate(value)
      } else if (idFields.includes(key) && value !== undefined && value !== null) {
        // ID 字段转换为字符串
        cleaned[key] = String(value)
      } else if (isRequired) {
        // 如果是必填字段，直接保留
        cleaned[key] = value
      } else if (key === 'purchaseOrderInfoDTOList' && Array.isArray(value)) {
        // 处理嵌套数组：过滤掉无效项（goods 或 warehouse 为空的项）
        const validItems = value
          .filter(item => {
            // 只保留 goods 和 warehouse 都不为空的项
            const goods = item.goods
            const warehouse = item.warehouse
            const goodsStr = goods !== undefined && goods !== null ? String(goods).trim() : ''
            // warehouse 是字符串类型，检查是否不为空
            const warehouseStr = warehouse !== undefined && warehouse !== null ? String(warehouse).trim() : ''
            return goodsStr !== '' && warehouseStr !== ''
          })
          .map(item => {
            const cleanedItem: any = {}
            Object.keys(item).forEach(itemKey => {
              const itemValue = (item as any)[itemKey]
              // 详情项中的必填字段
              const detailRequiredFields = ['goods', 'nums', 'price', 'total', 'tpt', 'unit', 'warehouse']
              const isDetailRequired = detailRequiredFields.includes(itemKey)
              
              // ID 字段转换为字符串
              if (detailIdFields.includes(itemKey) && itemValue !== undefined && itemValue !== null) {
                cleanedItem[itemKey] = String(itemValue)
              } else if (isDetailRequired || (itemValue !== undefined && itemValue !== null && itemValue !== '')) {
                // 必填字段保留，可选字段移除空值
                cleanedItem[itemKey] = itemValue
              } else if (itemValue === 0 || itemValue === false) {
                // 保留数字 0 和 false
                cleanedItem[itemKey] = itemValue
              }
            })
            return cleanedItem
          })
        
        // 如果过滤后还有有效项，才添加到 cleaned 中
        if (validItems.length > 0) {
          cleaned[key] = validItems
        }
      } else if (value !== undefined && value !== null && value !== '') {
        // 可选字段：移除空字符串和 null/undefined
        cleaned[key] = value
      } else if (value === 0 || value === false || (Array.isArray(value) && value.length === 0)) {
        // 保留数字 0、false、空数组
        cleaned[key] = value
      }
    })
    
    return cleaned
  }

  /**
   * 导入采购订单数据
   * 接口路径: /j3-purchase/purchase-order/import-bor
   * 请求方法: POST
   * 请求类型: multipart/form-data
   * @param file 要上传的Excel文件
   * @returns 响应数据
   */
  static async importTemplate(): Promise<Blob> {
    return this.http.getFile(`${currBaseUrl}/import/template`, {}, { responseType: 'blob' })
  }

  static async importPurchaseOrders(file: File): Promise<ApiResponse<string>> {
    if (!file || !/\.xlsx?$/i.test(file.name)) throw new Error('请选择 .xlsx 或 .xls 格式的Excel文件')
    if (file.size > 5 * 1024 * 1024) throw new Error('Excel文件最大5MiB')
    const result = await this.http.postWithFile<string>(`${currBaseUrl}/import-bor`, { file }, { showLoading: true })
    if (result.code !== 10000) throw new Error(result.message || '导入失败，整文件未保存')
    return result
  }

  /**
   * 导出简单报表
   * 接口路径: /purchase-order/export-bor
   * 请求方法: GET
   * 请求数据类型: application/x-www-form-urlencoded
   * 响应数据类型: 文件流
   * @param pid 订单ID，字符串类型，必须
   * @returns 响应数据，文件流，包含 data 和 headers
   */
  private static exportIds(ids: (string | number)[]): string[] {
    const values = ids.map(id => String(id ?? '').trim())
    if (!values.length || values.length > 200 || values.some(id => !id || id === '0') || new Set(values).size !== values.length) throw new Error('请选择1到200张不同且有效的采购订单')
    return values
  }

  static async exportSimpleReport(pid: string | number): Promise<any> {
    const ids = this.exportIds(String(pid ?? '').split(','))
    const result = await this.http.getFile(`${currBaseUrl}/export-bor`, {pid: ids.join(',')}, {responseType:'blob',showLoading:true})
    if (result instanceof Blob) return {data:result,headers:{'content-type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','content-disposition':'attachment; filename=purchase-orders.xlsx'}}
    if (!(result?.data instanceof Blob)) throw new Error(result?.data?.message || '导出失败，未返回Excel文件')
    return result
  }

  static async exportDetailReport(ids: (string | number)[]): Promise<any> {
    const result = await this.http.post<string>(`${currBaseUrl}/export/detail`, this.exportIds(ids), {upType:DataUpType.json,showLoading:true})
    if (result.code !== 10000 || typeof result.data !== 'string') throw new Error(result.message || '导出失败，未返回Excel文件')
    let binary: string
    try { binary = atob(result.data) } catch { throw new Error('导出文件格式无效，请重试') }
    if (!binary.startsWith('PK')) throw new Error('导出文件格式无效，请重试')
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0))
    return {data:new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}),headers:{'content-type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','content-disposition':'attachment; filename=purchase-order-details.xlsx'}}
  }
}
