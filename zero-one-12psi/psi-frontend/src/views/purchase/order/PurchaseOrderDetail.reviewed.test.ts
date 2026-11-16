import {beforeEach,describe,expect,it,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'
import {defineComponent,reactive} from 'vue'
import ElementPlus,{ElMessageBox} from 'element-plus'
const api=vi.hoisted(()=>({getDocument:vi.fn(),check:vi.fn(),audit:vi.fn(),revise:vi.fn()}))
vi.mock('@/apis/purchase/purchaseOrder',()=>({PurchaseNoteAPI:api}))
vi.mock('@/components/documentform/DocumentForm.vue',()=>({default:{name:'DocumentForm',template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Supplier.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/goodSearchConpoent/Warehouse.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationpoptable/OperationPopTable.vue',()=>({default:{template:'<div />'}}))
import Detail from './PurchaseOrderDetailDialog.vue'
const Form=defineComponent({setup(_,{expose}){const formdata=reactive<Record<string,any>>({});expose({formdata});return {formdata}},template:'<input aria-label="测试采购备注" v-model="formdata.remarks" />'})
function document(checked=0){return {version:'a'.repeat(64),header:{id:'purchase-a',number:'QA-SNAPSHOT',time_text:'2026-11-15 12:00:00',supplier:'supplier-a',supplierName:'测试供应商',total:200,actual:226,money:0,cost:0,file:'[]',check:checked,examine:0},items:[{id:'line-a',goods:'goods-a',goodsName:'测试商品',warehouse:'warehouse-a',warehouseName:'测试仓库',unit:'unit',price:100,nums:2,discount:0,dsc:0,total:200,tax:13,tat:26,tpt:226,serial:'[]'}]}}
async function open(checked=0){api.getDocument.mockResolvedValue({code:10000,data:document(checked)});const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]});await router.push('/');const wrapper=mount(Detail,{props:{visible:true,record:{id:'purchase-a'}},global:{plugins:[createPinia(),router,ElementPlus],stubs:{DocumentForm:Form,ElDialog:{props:['modelValue'],template:'<div v-if="modelValue"><slot /><slot name="footer" /></div>'}}}});await flushPromises();return wrapper}
async function button(wrapper:Awaited<ReturnType<typeof open>>,name:string){await wrapper.findAll('button').find(b=>b.text()===name)!.trigger('click');await flushPromises()}
describe('reviewed purchase detail actions',()=>{
 beforeEach(()=>{vi.restoreAllMocks();vi.clearAllMocks();vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>);api.check.mockResolvedValue({code:10000});api.audit.mockResolvedValue({code:10000})})
 it('checks exactly the loaded version',async()=>{const wrapper=await open();try{await button(wrapper,'核对');expect(api.check).toHaveBeenCalledWith(['purchase-a'],true,'a'.repeat(64))}finally{wrapper.unmount()}})
 it('posts exactly the reviewed checked version',async()=>{const wrapper=await open(1);try{await button(wrapper,'审核');expect(api.audit).toHaveBeenCalledWith(['purchase-a'],true,'a'.repeat(64))}finally{wrapper.unmount()}})
 it('blocks checking unsaved edits and keeps them visible',async()=>{const wrapper=await open();try{await wrapper.find('input[aria-label="测试采购备注"]').setValue('未保存的备注');await button(wrapper,'核对');expect(api.check).not.toHaveBeenCalled();expect(wrapper.text()).toContain('请先保存');expect((wrapper.find('input[aria-label="测试采购备注"]').element as HTMLInputElement).value).toBe('未保存的备注')}finally{wrapper.unmount()}})
 it('does not refresh or bless a stale version after the server rejects',async()=>{api.check.mockRejectedValue(new Error('采购单已变化；本次整批未处理'));const wrapper=await open();try{api.getDocument.mockClear();await button(wrapper,'核对');expect(wrapper.text()).toContain('采购单已变化');expect(api.getDocument).not.toHaveBeenCalled();expect(wrapper.emitted('changed')).toBeUndefined()}finally{wrapper.unmount()}})
 it('rechecks local edits made while the confirmation is open',async()=>{let confirm!:(v:any)=>void;vi.mocked(ElMessageBox.confirm).mockImplementation(()=>new Promise(resolve=>{confirm=resolve}));const wrapper=await open();try{await button(wrapper,'核对');await wrapper.find('input[aria-label="测试采购备注"]').setValue('确认期间变更');confirm('confirm');await flushPromises();expect(api.check).not.toHaveBeenCalled();expect(wrapper.text()).toContain('确认期间内容发生变化')}finally{wrapper.unmount()}})
})
