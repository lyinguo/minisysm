/*
 * @Author: f1-duanhong 1271736670@qq.com
 * @Date: 2025-10-29 23:20:00
 * @LastEditors: f1-duanhong 1271736670@qq.com
 * @LastEditTime: 2025-11-12 09:39:26
 * @FilePath: \psi-frontend\src\apis\warehouse\check\index.ts
 * @Description: 仓库管理-库存盘点接口
 */
import { useHttp, type RequestCallback } from '@/plugins/http'
import type {
  PageDTO,
  InventoryVerifyDTO,
  OtherInListInfoDTO,
  OtherOutListInfoDTO,
  InventoryVerifyRequest,
  JsonVO
} from './type'

const currBaseUrl = '/j2-store/verify'
const http = useHttp()

// 通用请求处理函数
const handleRequest = async <T>(
  request: Promise<any>,
  success: RequestCallback,
  fail: RequestCallback
) => {
  try {
    const res = await request
    if (res.data) {
      success(res.data)
    } else {
      fail(res)
    }
  } catch (err) {
    fail(err)
  }
}

/**
 * @description 导出库存盘点单
 * @param success 成功回调
 * @param fail 失败回调
 */
export const exportInventoryVerify = async (
  success: RequestCallback,
  fail: RequestCallback
) => {
  try {
    const res = await http.getFile(`${currBaseUrl}/export`, {}, {
      showLoading: true,
      responseType: 'blob',
      timeout: 600000
    })
    const blob: Blob | null =
      res instanceof Blob
        ? res
        : res?.data instanceof Blob
          ? res.data
          : res?.data != null
            ? new Blob([res.data])
            : null
    if (!blob) {
      fail(new Error('导出响应为空'))
      return
    }
    const contentType = String(
      res?.headers?.['content-type'] || blob.type || ''
    ).toLowerCase()
    if (contentType.includes('application/json') || contentType.includes('text/')) {
      const text = await blob.text()
      try {
        const json = JSON.parse(text)
        fail(
          new Error(
            (typeof json.data === 'string' && json.data) ||
              json.message ||
              '导出失败'
          )
        )
      } catch {
        fail(new Error(text || '导出失败'))
      }
      return
    }
    success(blob)
  } catch (err) {
    fail(err)
  }
}

/**
 * @description 获取盘盈单数据
 * @param params 库存盘点请求参数
 * @param success 成功回调
 * @param fail 失败回调
 */
export const getInventoryPlus = async (
  params: InventoryVerifyRequest | InventoryVerifyDTO[],
  success: RequestCallback,
  fail: RequestCallback
) => {
  // 后端接收的是 List<InventoryVerifyDTO> 数组，不是包装对象
  const body = Array.isArray(params) ? params : params.inventoryVerifyList || []
  return handleRequest(
    http.post<JsonVO<PageDTO<OtherInListInfoDTO>>>(`${currBaseUrl}/inventoryPlus`, body, {
      showLoading: true
    }),
    success,
    fail
  )
}

/**
 * @description 获取盘亏单数据
 * @param params 库存盘点请求参数
 * @param success 成功回调
 * @param fail 失败回调
 */
export const getInventoryReduce = async (
  params: InventoryVerifyRequest | InventoryVerifyDTO[],
  success: RequestCallback,
  fail: RequestCallback
) => {
  const body = Array.isArray(params) ? params : params.inventoryVerifyList || []
  return handleRequest(
    http.post<JsonVO<PageDTO<OtherOutListInfoDTO>>>(`${currBaseUrl}/inventoryReduce`, body, {
      showLoading: true
    }),
    success,
    fail
  )
}

// 盘点类型枚举
export const InventoryType = {
  PLUS: 'plus', // 盘盈
  REDUCE: 'reduce' // 盘亏
} as const

// 盘点状态枚举
export const InventoryStatus = {
  PENDING: 0, // 待盘点
  COUNTED: 1, // 已盘点
  VERIFIED: 2 // 已审核
} as const

// 差异类型枚举
export const DifferenceType = {
  NONE: 0, // 无差异
  PLUS: 1, // 盘盈
  REDUCE: -1 // 盘亏
} as const
