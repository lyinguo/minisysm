import { useHttp } from '@/plugins/http'

const http = useHttp()

/** 其它收入单 */
export const OtherIncomeDocAPI = {
  list: (params: Record<string, unknown>) => http.get('/finance/other-income/list', params)
}

/** 其它支出单 */
export const OtherExpenseDocAPI = {
  list: (params: Record<string, unknown>) => http.get('/finance/other-expense/list', params)
}

/** 购销费用 */
export const TradeExpenseAPI = {
  list: (params: Record<string, unknown>) => http.get('/finance/trade-expense/list', params)
}

/** 购销发票 */
export const TradeInvoiceAPI = {
  list: (params: Record<string, unknown>) => http.get('/finance/trade-invoice/list/invoice', params),
  add: (body: unknown) => http.post('/finance/trade-invoice/add', body),
  report: (params: Record<string, unknown>) => http.get('/finance/trade-invoice/list/report', params),
  exportReport: (ids: string[]) => http.post('/finance/trade-invoice/export/report', ids, { responseType: 'blob' })
}
