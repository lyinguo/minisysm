import type { PurchaseNoteAddDTO } from '@/apis/purchase/purchaseOrder/type'
const round = (value: number) => Number(value.toFixed(4))
function numeric(value: any, field: string, optional = false) {
  if (optional && (value == null || value === '')) return 0
  const number = Number(value)
  if (value == null || value === '' || !Number.isFinite(number) || number < 0) throw new Error(`${field}请输入有效的非负数字`)
  return number
}
export function purchaseSelectionRows(products: Record<string, any>[], original: Record<string, any> = {}) {
  return products.map(product => ({
    productName: product.name || product.productName || '', productCode: product.code || product.productCode || '',
    spec: product.model || product.spec || '', attr: typeof product.attr === 'string' ? product.attr : '',
    unit: product.unit || '', warehouse: original.warehouse || '', warehouseId: original.warehouseId || null,
    price: product.purchasePrice ?? product.price ?? 0, quantity: product.quantity ?? 1,
    taxRate: original.taxRate ?? '', discount: 0, amount: 0, taxAmount: 0, total: 0, remark: '',
    key: product.id || product.key || '', goodsId: product.id || product.key || '', batch: '', mfd: '', serial: '[]'
  }))
}
export function purchaseEntryPayload(header: Record<string, any>, supplier: string, rows: Record<string, any>[], form: Record<string, any>): PurchaseNoteAddDTO {
  if (!supplier) throw new Error('请选择供应商')
  if (!header.documentDate || !header.documentNumber?.trim()) throw new Error('请填写单据日期和编号')
  const selected = rows.filter(row => row.productName)
  if (!selected.length) throw new Error('请至少添加一条商品数据')
  const account = String(form.settlementAccount || '')
  const money = numeric(form.paidAmount, '实付金额', true), cost = numeric(form.documentFee, '单据费用', true)
  if (money > 0 && (!account || account === '0')) throw new Error('填写实付金额时请选择结算账户')
  const files = form.documentAttachment || []
  if (files.some((file: any) => !file.url || file.status && file.status !== 'success')) throw new Error('附件尚未上传成功，请重试或移除失败附件')
  const details = selected.map((row, index) => {
    const goods = String(row.goodsId || row.key || ''), warehouse = String(row.warehouseId || ''), unit = String(row.unit || '')
    if (!goods || !warehouse || warehouse === '0' || !unit) throw new Error(`请检查第 ${index + 1} 行商品、仓库和单位`)
    const price = numeric(row.price, `第 ${index + 1} 行单价`), nums = numeric(row.quantity, `第 ${index + 1} 行数量`)
    const discount = numeric(row.discount, '折扣', true), tax = numeric(row.taxRate, '税率', true)
    if (!nums || discount > 100 || tax > 100) throw new Error(`第 ${index + 1} 行数量必须大于零，折扣和税率须在0到100之间`)
    const gross = round(price * nums), dsc = round(gross * discount / 100), total = round(gross - dsc), tat = round(total * tax / 100), tpt = round(total + tat)
    return {
      goods, warehouse, unit, price, nums, discount, dsc, total, tax, tat, tpt,
      attr: row.attr || '', batch: row.batch || '', mfd: row.mfd || '', serial: typeof row.serial === 'string' ? row.serial : JSON.stringify(row.serial || []),
      source: '0', account, actual: 0, cost, data: row.remark || '', data2: '', logistics: '', money, name: row.productName,
      noteTotal: 0, number: header.documentNumber.trim(), people: String(form.relatedPerson || ''), supplier, time: header.documentDate
    }
  })
  const total = round(details.reduce((sum, line) => sum + line.total, 0)), actual = round(details.reduce((sum, line) => sum + line.tpt, 0))
  if (money > actual) throw new Error('实付金额不能超过实际金额')
  return {
    purchaseNoteBuyDTO: {
      supplier, time: header.documentDate, number: header.documentNumber.trim(), total, actual, money, cost, account,
      people: String(form.relatedPerson || ''), source: '0', data: form.remarks || '',
      file: JSON.stringify(files.map((file: any) => ({ name: file.name || file.url.split('/').pop(), url: file.url }))), logistics: form.logistics?.number || ''
    },
    purchaseNoteInfoDTOS: details.map(line => ({ ...line, actual, noteTotal: total }))
  }
}
