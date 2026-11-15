import {beforeEach,describe,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'
import ElementPlus from 'element-plus'
const api=vi.hoisted(()=>({auditPurchaseOrders:vi.fn(),orderStatus:vi.fn()}))
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:api}))
vi.mock('@/components/documentform/DocumentForm.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Supplier.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Warehouse.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationpoptable/OperationPopTable.vue',()=>({default:{template:'<div />'}}))
import Detail from './PurchaseBookDetailDialog.vue'
async function open(){const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]});await router.push('/');await router.isReady();const wrapper=mount(Detail,{props:{visible:true,record:{id:'actual-order-uuid',auditStatus:'未审核',detailData:[{goods:'goods-uuid',name:'实际商品',nums:2,price:100,tax:13,tat:26,amount:200,tpt:226,purchaseOrderOtherDetailDTO:{supplier:'supplier-uuid',number:'QA-ORDER',time:'2026-11-15',actual:226,total:200}}]}},global:{plugins:[createPinia(),router,ElementPlus],stubs:{'el-dialog':{template:'<div><slot /><slot name="footer" /></div>'}}}});await flushPromises();return wrapper}
describe('actual order approval dialog',()=>{
 beforeEach(()=>{vi.resetAllMocks()})
 it('waits for server approval and status read before showing actual audited state',async()=>{api.auditPurchaseOrders.mockResolvedValue({code:10000});api.orderStatus.mockResolvedValue({code:10000,data:{examine:1}});const wrapper=await open();try{expect(wrapper.find('.approved-stamp').exists()).toBe(false);await wrapper.findAll('button').find(b=>b.text()==='审核')!.trigger('click');await flushPromises();expect(api.auditPurchaseOrders).toHaveBeenCalledWith(['actual-order-uuid'],1);expect(api.orderStatus).toHaveBeenCalledWith('actual-order-uuid');expect(wrapper.find('.approved-stamp').exists()).toBe(true);expect(wrapper.emitted('audit')).toHaveLength(1)}finally{wrapper.unmount()}})
 it('keeps rejection visible and never fakes an audited stamp',async()=>{api.auditPurchaseOrders.mockResolvedValue({code:9995,message:'供货关系已停用'});const wrapper=await open();try{await wrapper.findAll('button').find(b=>b.text()==='审核')!.trigger('click');await flushPromises();expect(wrapper.text()).toContain('供货关系已停用');expect(wrapper.find('.approved-stamp').exists()).toBe(false);expect(api.orderStatus).not.toHaveBeenCalled();expect(wrapper.emitted('audit')).toBeUndefined()}finally{wrapper.unmount()}})
})
