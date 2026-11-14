/**
 * 仓库/库存单据编号生成
 * - 唯一：时间戳片段 + 加密随机，碰撞概率极低
 * - 无明显连续规律：随机段不可预测
 */

function toBase36(n: number): string {
  return Math.abs(Math.floor(n)).toString(36).toUpperCase()
}

function randomChars(length: number): string {
  const alphabet = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ' // 去掉易混淆 I/O
  const bytes = new Uint8Array(length)
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(bytes)
  } else {
    for (let i = 0; i < length; i++) bytes[i] = Math.floor(Math.random() * 256)
  }
  let out = ''
  for (let i = 0; i < length; i++) {
    out += alphabet[bytes[i] % alphabet.length]
  }
  return out
}

/** 仓库单据前缀 */
export const BillPrefix = {
  OTHER_IN: 'QTRKD', // 其它入库
  OTHER_OUT: 'QTCKD', // 其它出库
  TRANSFER: 'DBD', // 调拨
  INVENTORY_CHECK: 'KCPD' // 库存盘点
} as const

export type BillPrefixType = (typeof BillPrefix)[keyof typeof BillPrefix] | string

/**
 * 生成唯一单据编号
 * 格式：前缀 + 时间(base36) + 随机段，例：QTRKD-M8K2P9-X7Q4A2
 */
export function generateBillNumber(prefix: BillPrefixType): string {
  const timePart = toBase36(Date.now())
  const randPart = randomChars(8)
  const safePrefix = String(prefix || 'BILL').replace(/[^A-Za-z0-9]/g, '').toUpperCase() || 'BILL'
  return `${safePrefix}${timePart}${randPart}`
}

/** @deprecated 兼容旧调用名 */
export function generateBillNo(prefix: BillPrefixType): string {
  return generateBillNumber(prefix)
}
