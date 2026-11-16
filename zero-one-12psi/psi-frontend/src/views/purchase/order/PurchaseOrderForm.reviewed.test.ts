import {beforeEach,describe,expect,it,vi} from 'vitest'
import {shallowMount,flushPromises} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {ElMessageBox} from 'element-plus'
const api=vi.hoisted(()=>({getList:vi.fn(),check:vi.fn(),audit:vi.fn(),importFile:vi.fn(),importTemplate:vi.fn()}))
vi.mock('@/apis/purchase/purchaseOrder',()=>({PurchaseNoteAPI:api}))
vi.mock('./PurchaseOrderDetailDialog.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationbuttons/OperationButtons.vue',()=>({default:{template:'<div />'}}))
import Form from './PurchaseOrderForm.vue'
const rows=()=>[{id:'a',version:'a'.repeat(64),number:'QA-A',examine:0,checkStatus:0},{id:'b',version:'b'.repeat(64),number:'QA-B',examine:0,checkStatus:0}]
async function open(){const wrapper=shallowMount(Form,{global:{plugins:[createPinia()],stubs:{ElPopover:{template:'<div><slot name="reference" /><slot /></div>'},ElButton:{emits:['click'],template:'<button @click="$emit(\'click\')"><slot /></button>'},ElAlert:{props:['title'],template:'<p role="alert">{{title}}<slot /></p>'},ElTable:{name:'ElTable',props:['data'],methods:{clearSelection(){}},template:'<div />'}}}});await flushPromises();return wrapper}
async function select(wrapper:Awaited<ReturnType<typeof open>>,value:any[]){wrapper.findComponent({name:'ElTable'}).vm.$emit('selection-change',value);await flushPromises()}
async function command(wrapper:Awaited<ReturnType<typeof open>>,text='核对'){await wrapper.findAll('li').find(li=>li.text()===text)!.trigger('click');await flushPromises()}
describe('complete reviewed purchase selection',()=>{
 beforeEach(()=>{vi.restoreAllMocks();vi.clearAllMocks();vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}unobserve(){}});api.getList.mockResolvedValue({code:10000,data:{total:2,rows:rows()}});api.check.mockResolvedValue({code:10000});vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)})
 it('sends every displayed row ID and version',async()=>{const wrapper=await open();try{const displayed=wrapper.findComponent({name:'ElTable'}).props('data');await select(wrapper,displayed);await command(wrapper);expect(api.check).toHaveBeenCalledWith(['a','b'],true,{a:'a'.repeat(64),b:'b'.repeat(64)})}finally{wrapper.unmount()}})
 it('refuses a missing ID or version without filtering to a partial batch',async()=>{for(const bad of [{...rows()[1],id:undefined},{...rows()[1],version:undefined}]){const wrapper=await open();try{await select(wrapper,[rows()[0],bad]);await command(wrapper);expect(api.check).not.toHaveBeenCalled();expect(wrapper.text()).toContain('整批不能提交')}finally{wrapper.unmount()}}})
 it('preserves selection and guidance after a stale server rejection',async()=>{api.check.mockRejectedValue(new Error('采购单已变化；本次整批未处理'));const wrapper=await open();try{await select(wrapper,rows());api.getList.mockClear();await command(wrapper);expect(wrapper.text()).toContain('采购单已变化');expect(wrapper.findAll('button').some(b=>b.text()==='操作')).toBe(true);expect(api.getList).not.toHaveBeenCalled()}finally{wrapper.unmount()}})
 it('does not submit another command while one is pending',async()=>{let complete!:(v:any)=>void;api.check.mockImplementation(()=>new Promise(resolve=>{complete=resolve}));const wrapper=await open();try{await select(wrapper,rows());await command(wrapper);await command(wrapper);expect(api.check).toHaveBeenCalledTimes(1);complete({code:10000});await flushPromises()}finally{wrapper.unmount()}})
 it('distinguishes successful submission from failed refresh',async()=>{const wrapper=await open();try{await select(wrapper,rows());api.getList.mockRejectedValue(new Error('QA refresh unavailable'));await command(wrapper);expect(wrapper.text()).toContain('操作已提交');expect(wrapper.text()).toContain('列表刷新失败')}finally{wrapper.unmount()}})
})
