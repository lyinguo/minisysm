/** 单据类型：界面中文 ↔ 后端 mold 代码 */
export const MOLD_LABEL_TO_CODE: Record<string, string> = {
  收款单: 'imy',
  付款单: 'omy',
  销售单: 'sell',
  销售退货单: 'sre',
  其它收入单: 'ice',
  其他收入单: 'ice',
  采购单: 'buy',
  采购退货单: 'bre',
  其它支出单: 'oce',
  其他支出单: 'oce'
}

export const MOLD_CODE_TO_LABEL: Record<string, string> = {
  imy: '收款单',
  omy: '付款单',
  sell: '销售单',
  sre: '销售退货单',
  ice: '其它收入单',
  buy: '采购单',
  bre: '采购退货单',
  oce: '其它支出单'
}

/** 核销类别：界面中文 ↔ 后端 bill 代码 */
export const BILL_LABEL_TO_CODE: Record<string, string> = {
  预收: 'cia',
  应收: 're',
  预付: 'pia',
  应付: 'cw',
  销退: 'sre',
  销售: 'sell',
  采购: 'buy',
  购退: 'bre'
}

export const BILL_CODE_TO_LABEL: Record<string, string> = {
  cia: '预收',
  re: '应收',
  pia: '预付',
  cw: '应付'
}

/** 待核销列表 type2 参数 */
export const MOLD_TO_PENDING_TYPE2: Record<string, number> = {
  imy: 0,
  sell: 1,
  sre: 2,
  ice: 3
}

export function moldLabelToCode(label?: string): string {
  if (!label) return ''
  return MOLD_LABEL_TO_CODE[label] || label
}

export function moldCodeToLabel(code?: string): string {
  if (!code) return ''
  return MOLD_CODE_TO_LABEL[code] || code
}

export function billLabelToCode(label?: string): string {
  if (!label) return ''
  return BILL_LABEL_TO_CODE[label] || label
}

export function billCodeToLabel(code?: string): string {
  if (!code) return ''
  return BILL_CODE_TO_LABEL[code] || code
}
