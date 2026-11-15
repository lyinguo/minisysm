import {beforeEach,describe,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import ElementPlus from 'element-plus'
const api=vi.hoisted(()=>({receivePreview:vi.fn(),receiveOrder:vi.fn()}))
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:api}))
import Dialog from './PurchaseReceiveDialog.vue'
const quote={header:{id:'order-uuid',number:'ORDER-1',supplierName:'实际供应商'},items:[{id:'line-uuid',name:'实际商品',number:'G001',nums:3,handle:1,reserved:1,available:1,price:100,discountPercent:10,taxPercent:13,warehouseName:'实际仓库'}],drafts:[{id:'pending-uuid',number:'RECEIVE-OLD'}]}
function open(){return mount(Dialog,{props:{visible:true,orderId:'order-uuid'},global:{plugins:[ElementPlus],stubs:{'el-dialog':{template:'<div><slot /><slot name="footer" /></div>'}}}})}
describe('source receiving generation',()=>{
 beforeEach(()=>{vi.resetAllMocks();api.receivePreview.mockResolvedValue({code:10000,data:quote})})
 it('shows actual source, pending quantities and discount/tax while sending only source IDs and requested quantities',async()=>{api.receiveOrder.mockResolvedValue({code:10000,data:{id:'new-uuid',number:'RECEIVE-NEW'}});const wrapper=open();try{await flushPromises();expect(wrapper.text()).toContain('实际供应商');expect(wrapper.text()).toContain('101.7000');expect(wrapper.text()).toContain('RECEIVE-OLD');await wrapper.findAll('button').find(b=>b.text()==='生成采购草稿')!.trigger('click');await flushPromises();expect(api.receiveOrder).toHaveBeenCalledWith(expect.objectContaining({id:'order-uuid',items:[{id:'line-uuid',nums:1}]}));expect(wrapper.emitted('created')?.[0]?.[0]).toEqual({id:'new-uuid',number:'RECEIVE-NEW'})}finally{wrapper.unmount()}})
 it('keeps rejected request quantities visible for correction and does not fake generation success',async()=>{api.receiveOrder.mockResolvedValue({code:9995,message:'剩余数量已经被占用'});const wrapper=open();try{await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='生成采购草稿')!.trigger('click');await flushPromises();expect(wrapper.text()).toContain('剩余数量已经被占用');expect(wrapper.text()).toContain('101.7000');expect(wrapper.emitted('created')).toBeUndefined()}finally{wrapper.unmount()}})
 it('does not allow generation when all quantity is already received or reserved',async()=>{api.receivePreview.mockResolvedValue({code:10000,data:{...quote,items:[{...quote.items[0],available:0}]}});const wrapper=open();try{await flushPromises();expect(wrapper.findAll('button').find(b=>b.text()==='生成采购草稿')!.attributes('disabled')).toBeDefined();expect(wrapper.text()).toContain('已生成的待入库采购单')}finally{wrapper.unmount()}})
})
