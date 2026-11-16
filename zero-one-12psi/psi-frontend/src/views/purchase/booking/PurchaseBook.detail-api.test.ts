import {beforeEach,describe,expect,it,vi} from 'vitest'
const http=vi.hoisted(()=>({put:vi.fn()}))
vi.mock('@/plugins/http',()=>({useHttp:()=>http,DataUpType:{json:'json'}}))
import {PurchaseOrderAPI} from '@/apis/purchase/PurchaseBooking/order'
const body=()=>({id:'actual-order',number:'QA-DETAIL',supplier:'actual-supplier',people:'',time:'2026-11-15',arrival:'2026-11-16',total:.4001,actual:.4521,data:'',logistics:'',file:'[]',purchaseOrderInfoDTOList:[{goods:'actual-goods',warehouse:'actual-warehouse',unit:'unit',price:1.0001,nums:.5,discount:20,dsc:.1,total:.4001,tax:13,tat:.052,tpt:.4521}]})
describe('order detail update transport',()=>{
 beforeEach(()=>vi.resetAllMocks())
 it('allows optional person and sends explicit text clears plus unchanged four-decimal amounts',async()=>{http.put.mockResolvedValue({code:10000,data:'actual-order'});await PurchaseOrderAPI.updatePurchaseOrder(body());expect(http.put).toHaveBeenCalledWith('/j3-purchase/purchase-order/update',body(),{upType:'json',showLoading:true})})
 it('rejects a missing warehouse instead of silently saving a partial document',async()=>{const request=body();request.purchaseOrderInfoDTOList[0].warehouse='';await expect(PurchaseOrderAPI.updatePurchaseOrder(request)).rejects.toThrow('仓库ID不能为空');expect(http.put).not.toHaveBeenCalled()})
})
