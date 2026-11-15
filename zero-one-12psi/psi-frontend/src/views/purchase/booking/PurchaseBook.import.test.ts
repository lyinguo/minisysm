import {beforeEach,describe,expect,it,vi} from 'vitest'
const http=vi.hoisted(()=>({getFile:vi.fn(),postWithFile:vi.fn()}))
vi.mock('@/plugins/http',()=>({useHttp:()=>http,DataUpType:{json:'json'}}))
import {PurchaseOrderAPI} from '@/apis/purchase/PurchaseBooking/order'
describe('order workbook API',()=>{
 beforeEach(()=>vi.resetAllMocks())
 it('downloads the server workbook as a file',async()=>{const blob=new Blob(['xlsx']);http.getFile.mockResolvedValue(blob);expect(await PurchaseOrderAPI.importTemplate()).toBe(blob);expect(http.getFile).toHaveBeenCalledWith('/j3-purchase/purchase-order/import/template',{}, {responseType:'blob'})})
 it('surfaces business refusal rather than returning success to the upload dialog',async()=>{const file=new File(['xlsx'],'orders.xlsx');http.postWithFile.mockResolvedValue({code:9995,message:'第4行：供货关系已停用'});await expect(PurchaseOrderAPI.importPurchaseOrders(file)).rejects.toThrow('第4行：供货关系已停用');expect(http.postWithFile).toHaveBeenCalledWith('/j3-purchase/purchase-order/import-bor',{file},{showLoading:true})})
 it('does not upload a file exceeding the documented size',async()=>{await expect(PurchaseOrderAPI.importPurchaseOrders(new File([new Uint8Array(5*1024*1024+1)],'large.xlsx'))).rejects.toThrow('最大5MiB');expect(http.postWithFile).not.toHaveBeenCalled()})
})
