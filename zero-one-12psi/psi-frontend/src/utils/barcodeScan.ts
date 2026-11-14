/** 条码扫描展示文本（与后端 CodeServiceImpl 保持一致） */

export interface BarcodeScanFields {
  name: string
  info: string
  type: number
  data?: string
}

/** 二维码扫描后展示的完整文本 */
export function buildQrScanText(fields: BarcodeScanFields): string {
  const lines = [
    '[进销存条码]',
    `名称：${fields.name || ''}`,
    `内容：${fields.info || ''}`,
    `类型：${fields.type === 1 ? '二维码' : '条形码'}`
  ]
  if (fields.data?.trim()) {
    lines.push(`备注：${fields.data.trim()}`)
  }
  return lines.join('\n')
}

/**
 * 一维条形码实际编码内容（单行，仅 ASCII）
 * 纯数字时加 PSI 前缀，避免被微信等识别为商品码而提示「未找到该商品」
 */
export function buildBarScanText(fields: Pick<BarcodeScanFields, 'info'>): string {
  const info = (fields.info || '').trim()
  if (/^\d{8,}$/.test(info)) {
    return `PSI${info}`
  }
  return info
}

/** 是否为易被手机当成商品码的纯数字条形码 */
export function isRetailLikeBarcode(info: string): boolean {
  return /^\d{8,}$/.test((info || '').trim())
}
