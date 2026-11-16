import {describe,expect,it,vi} from 'vitest'
const http=vi.hoisted(()=>({put:vi.fn(),get:vi.fn()}))
vi.mock('@/plugins/http',()=>({useHttp:()=>http,DataUpType:{json:1}}))
import {PurchaseOrderAPI} from './order'
describe('order approval identifiers',()=>{
 it('sends complete UUID and long string IDs without numeric parsing',async()=>{http.put.mockResolvedValue({code:10000,data:[]});const versions={'abc123-uuid':'0'.repeat(64),'9999999999999999999':'1'.repeat(64)};await PurchaseOrderAPI.auditPurchaseOrders(['abc123-uuid','9999999999999999999'],1,versions);expect(http.put).toHaveBeenCalledWith('/j3-purchase/purchase-order/audit',{ids:['abc123-uuid','9999999999999999999'],type:1,versions},expect.anything())})
 it('rejects the whole selection instead of filtering invalid or duplicate IDs',async()=>{await expect(PurchaseOrderAPI.auditPurchaseOrders(['valid',''],1)).rejects.toThrow();await expect(PurchaseOrderAPI.auditPurchaseOrders(['valid','valid'],1)).rejects.toThrow()})
})
