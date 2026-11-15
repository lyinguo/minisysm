import {beforeEach,describe,expect,it,vi} from 'vitest'
const http=vi.hoisted(()=>({getFile:vi.fn(),post:vi.fn()}))
vi.mock('@/plugins/http',()=>({useHttp:()=>http,DataUpType:{json:'json'}}))
import {PurchaseOrderAPI} from '@/apis/purchase/PurchaseBooking/order'
describe('actual order workbook response handling',()=>{
 beforeEach(()=>vi.resetAllMocks())
 it('decodes the JSON base64 contract to a binary workbook before download',async()=>{http.post.mockResolvedValue({code:10000,data:btoa('PKxlsx')});const result=await PurchaseOrderAPI.exportDetailReport(['actual-a','actual-b']);expect(http.post).toHaveBeenCalledWith('/j3-purchase/purchase-order/export/detail',['actual-a','actual-b'],{upType:'json',showLoading:true});expect(result.data).toBeInstanceOf(Blob);expect(result.data.size).toBe(6);expect(result.headers['content-disposition']).toContain('.xlsx')})
 it('rejects business errors and non-workbook base64 rather than downloading JSON as xlsx',async()=>{http.post.mockResolvedValueOnce({code:9995,message:'采购订单不存在'});await expect(PurchaseOrderAPI.exportDetailReport(['actual-a'])).rejects.toThrow('采购订单不存在');http.post.mockResolvedValueOnce({code:10000,data:btoa('{"code":9995}')});await expect(PurchaseOrderAPI.exportDetailReport(['actual-a'])).rejects.toThrow('格式无效')})
 it('exports every CSV selection and normalizes blob responses',async()=>{const blob=new Blob(['PKxlsx']);http.getFile.mockResolvedValue(blob);const result=await PurchaseOrderAPI.exportSimpleReport('actual-a,actual-b');expect(http.getFile).toHaveBeenCalledWith('/j3-purchase/purchase-order/export-bor',{pid:'actual-a,actual-b'},{responseType:'blob',showLoading:true});expect(result.data).toBe(blob)})
 it('rejects duplicate/missing IDs without silently dropping selected orders',async()=>{for(const ids of [[],['a','a'],['a','']])await expect(PurchaseOrderAPI.exportDetailReport(ids)).rejects.toThrow('请选择');await expect(PurchaseOrderAPI.exportSimpleReport('a,')).rejects.toThrow('请选择');expect(http.post).not.toHaveBeenCalled();expect(http.getFile).not.toHaveBeenCalled()})
})
