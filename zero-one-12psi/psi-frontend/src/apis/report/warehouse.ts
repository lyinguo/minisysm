import { useHttp } from '@/plugins/http'

const http = useHttp()

export const WarehouseReportAPI = {
  balanceList: (params: Record<string, unknown>) => http.get('/report/balance/select', params),
  balanceExport: (params: Record<string, unknown>) =>
    http.getFile('/report/balance/export', params),
  detailList: (params: Record<string, unknown>) => http.get('/report/detail/list', params),
  detailExport: (params: Record<string, unknown>) =>
    http.getFile('/report/detail/export', params),
  summaryList: (params: Record<string, unknown>) => http.get('/report/summary/list', params),
  summaryExport: (params: Record<string, unknown>) =>
    http.getFile('/report/summary/export', params)
}
