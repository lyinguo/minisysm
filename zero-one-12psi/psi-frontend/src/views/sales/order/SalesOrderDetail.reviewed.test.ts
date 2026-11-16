import {beforeEach,describe,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'
import {defineComponent,reactive} from 'vue'
import ElementPlus,{ElMessageBox} from 'element-plus'
const api=vi.hoisted(()=>({getDocument:vi.fn(),checkSales:vi.fn(),examineSales:vi.fn(),updateSale:vi.fn()}))
vi.mock('@/apis/sales/order',()=>({saleOrderApi:api}))
vi.mock('@/stores/common',()=>({useCommonStore:()=>({orgTree:[],loadOrgTree:vi.fn().mockResolvedValue([])})}))
vi.mock('@/components/documentform/DocumentForm.vue',()=>({default:{name:'DocumentForm',template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Customer.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Warehouse.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationpoptable/OperationPopTable.vue',()=>({default:{template:'<div />'}}))
import Detail from './SalesOrderDetailDialog.vue'
const Form=defineComponent({setup(_,{expose}){const formdata=reactive<Record<string,any>>({});expose({formdata});return {formdata}},template:'<input aria-label="qa-remarks" v-model="formdata.remarks" />'})
function document(checked=0){return {version:'a'.repeat(64),header:{id:'sale-a',frame:'frame-a',number:'QA-SALE-REVIEW',time:'2026-11-15 12:00:00',customer:'customer-a',customerName:'QA customer',total:200,actual:226,money:0,cost:0,file:'[]',check:checked,examine:0},items:[{id:'line-a',goods:'goods-a',goodsName:'QA goods',warehouse:'warehouse-a',warehouseName:'QA warehouse',unit:'unit',price:100,nums:2,discount:1,total:200,tax:.13,tat:26,tpt:226,serial:'[]'}]}}
async function open(checked=0){api.getDocument.mockResolvedValue({code:10000,data:document(checked)});const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]});await router.push('/');const wrapper=mount(Detail,{props:{visible:true,record:{id:'sale-a'}},global:{plugins:[createPinia(),router,ElementPlus],stubs:{DocumentForm:Form,ElDialog:{props:['modelValue'],template:'<div v-if="modelValue"><slot /><slot name="footer" /></div>'}}}});await flushPromises();return wrapper}
async function button(wrapper:Awaited<ReturnType<typeof open>>,name:string){await wrapper.findAll('button').find(b=>b.text()===name)!.trigger('click');await flushPromises()}
describe('reviewed sales detail actions',()=>{
 beforeEach(()=>{vi.restoreAllMocks();vi.clearAllMocks();vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>);api.checkSales.mockResolvedValue({code:10000});api.examineSales.mockResolvedValue({code:10000})})
 it('checks exactly the displayed version',async()=>{const wrapper=await open();try{await button(wrapper,'核对');expect(api.checkSales).toHaveBeenCalledWith(['sale-a'],true,'a'.repeat(64))}finally{wrapper.unmount()}})
 it('posts exactly the displayed checked version',async()=>{const wrapper=await open(1);try{await button(wrapper,'审核');expect(api.examineSales).toHaveBeenCalledWith(['sale-a'],true,'a'.repeat(64))}finally{wrapper.unmount()}})
 it('keeps dirty fields without automatically saving or checking them',async()=>{const wrapper=await open();try{await wrapper.find('input[aria-label="qa-remarks"]').setValue('unsaved remark');await button(wrapper,'核对');expect(api.updateSale).not.toHaveBeenCalled();expect(api.checkSales).not.toHaveBeenCalled();expect((wrapper.find('input[aria-label="qa-remarks"]').element as HTMLInputElement).value).toBe('unsaved remark')}finally{wrapper.unmount()}})
 it('does not fetch and bless a new version when the server refuses the reviewed command',async()=>{api.checkSales.mockResolvedValue({code:9995,message:'stale reviewed sale'});const wrapper=await open();try{api.getDocument.mockClear();await button(wrapper,'核对');expect(api.getDocument).not.toHaveBeenCalled();expect(wrapper.emitted('changed')).toBeUndefined()}finally{wrapper.unmount()}})
 it('rechecks dirty fields after a delayed confirmation',async()=>{let confirm!:(v:any)=>void;vi.mocked(ElMessageBox.confirm).mockImplementation(()=>new Promise(resolve=>{confirm=resolve}));const wrapper=await open();try{await button(wrapper,'核对');await wrapper.find('input[aria-label="qa-remarks"]').setValue('changed during confirmation');confirm('confirm');await flushPromises();expect(api.checkSales).not.toHaveBeenCalled()}finally{wrapper.unmount()}})
 it('refuses a delayed confirmation after the detail closes',async()=>{let confirm!:(v:any)=>void;vi.mocked(ElMessageBox.confirm).mockImplementation(()=>new Promise(resolve=>{confirm=resolve}));const wrapper=await open();try{await button(wrapper,'核对');await wrapper.setProps({visible:false});confirm('confirm');await flushPromises();expect(api.checkSales).not.toHaveBeenCalled()}finally{wrapper.unmount()}})
})
