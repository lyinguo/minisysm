import {describe,it,expect,vi} from 'vitest'
import {shallowMount,flushPromises} from '@vue/test-utils'
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:{importTemplate:vi.fn()}}))
vi.mock('@/components/goodSearchConpoent',()=>({PurchaseSearchForm:{name:'PurchaseSearchForm',template:'<div />'}}))
vi.mock('./PurchaseBookDetailDialog.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationbuttons/OperationButtons.vue',()=>({default:{template:'<div />'}}))
import Form from './PurchaseBookForm.vue'
function open(){return shallowMount(Form,{global:{stubs:{ElTable:{name:'ElTable',props:['data'],template:'<div />'},OperationButtons:true,PurchaseBookDetailDialog:true}}})}
describe('order list display',()=>{
 it('uses names/dates/status labels while keeping UUID identity and four-decimal page totals',async()=>{const wrapper=open();try{wrapper.findComponent({name:'PurchaseSearchForm'}).vm.$emit('search',{}, {total:1,rows:[{id:'order-uuid',frame:'frame-uuid',frameName:'组织甲',supplier:'supplier-uuid',supplierName:'真实供应商',people:'person-uuid',peopleName:'真实人员',user:'user-uuid',userName:'真实制单人',number:'ORDER',documentTime:'2026-11-15 00:00:00',arrivalTime:'2026-11-16',examine:'1',examineName:'已审核',state:'3',stateName:'关闭',total:'1.0001',actual:'1.1301'}]});await flushPromises();expect(wrapper.findComponent({name:'ElTable'}).props('data')[0]).toMatchObject({id:'order-uuid',org:'组织甲',supplier:'真实供应商',contact:'真实人员',maker:'真实制单人',date:'2026-11-15 00:00:00',arrivalDate:'2026-11-16',auditStatus:'已审核',stockStatus:'关闭'});expect(wrapper.text()).toContain('本页单据金额：1.0001')}finally{wrapper.unmount()}})
 it('never interprets abnormal state as unaudited when labels are missing',async()=>{const wrapper=open();try{wrapper.findComponent({name:'PurchaseSearchForm'}).vm.$emit('search',{}, {total:1,rows:[{id:'uuid',examine:'2',state:'4',total:0,actual:0}]});await flushPromises();expect(wrapper.findComponent({name:'ElTable'}).props('data')[0]).toMatchObject({auditStatus:'异常(2)',stockStatus:'异常(4)'})}finally{wrapper.unmount()}})
})
