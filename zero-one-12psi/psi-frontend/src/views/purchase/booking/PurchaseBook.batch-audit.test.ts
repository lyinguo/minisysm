import {beforeEach,describe,expect,it,vi} from 'vitest'
import {shallowMount,flushPromises} from '@vue/test-utils'
const api=vi.hoisted(()=>({auditPurchaseOrders:vi.fn(),importTemplate:vi.fn()}))
const search=vi.hoisted(()=>vi.fn())
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:api}))
vi.mock('@/components/goodSearchConpoent',()=>({PurchaseSearchForm:{name:'PurchaseSearchForm',methods:{search},template:'<div />'}}))
vi.mock('./PurchaseBookDetailDialog.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationbuttons/OperationButtons.vue',()=>({default:{template:'<div />'}}))
import Form from './PurchaseBookForm.vue'
function open(){return shallowMount(Form,{global:{stubs:{PurchaseSearchForm:false,ElPopover:{template:'<div><slot name="reference" /><slot /></div>'},ElButton:{template:'<button @click="$emit(\'click\')"><slot /></button>'},ElAlert:{props:['title'],template:'<p role="alert">{{title}}</p>'},ElTable:{name:'ElTable',methods:{clearSelection(){}},template:'<div />'}}}})}
const rows=()=>[{id:'a',version:'0'.repeat(64),auditStatus:'未审核'},{id:'b',version:'1'.repeat(64),auditStatus:'未审核'}]
async function select(wrapper:any,selection:any[]){wrapper.findComponent({name:'ElTable'}).vm.$emit('selection-change',selection);await flushPromises()}
async function approve(wrapper:any){await wrapper.findAll('button').find((b:any)=>b.text()==='审核')!.trigger('click');await flushPromises()}
describe('complete batch approval selection',()=>{
 beforeEach(()=>{vi.resetAllMocks();search.mockResolvedValue(undefined)})
 it('sends every selected ID and its displayed version before refreshing current filters',async()=>{api.auditPurchaseOrders.mockResolvedValue({code:10000});const wrapper=open();try{await select(wrapper,rows());search.mockClear();await approve(wrapper);expect(api.auditPurchaseOrders).toHaveBeenCalledWith(['a','b'],1,{a:'0'.repeat(64),b:'1'.repeat(64)});expect(search).toHaveBeenCalledTimes(1)}finally{wrapper.unmount()}})
 it('rejects a missing member ID instead of approving the valid subset',async()=>{const wrapper=open();try{await select(wrapper,[rows()[0],{...rows()[1],id:undefined}]);await approve(wrapper);expect(api.auditPurchaseOrders).not.toHaveBeenCalled();expect(wrapper.text()).toContain('整批未处理')}finally{wrapper.unmount()}})
 it('requires all row versions and one applicable status without discarding selected rows',async()=>{for(const selection of [[rows()[0],{...rows()[1],version:undefined}],[rows()[0],{...rows()[1],auditStatus:'已审核'}]]){const wrapper=open();try{await select(wrapper,selection);await approve(wrapper);expect(api.auditPurchaseOrders).not.toHaveBeenCalled();expect(wrapper.find('[role="alert"]').exists()).toBe(true)}finally{wrapper.unmount()}}})
 it('keeps selection and conflict guidance after a stale server rejection',async()=>{api.auditPurchaseOrders.mockRejectedValue(new Error('选中订单已变化，请刷新列表重新核对；本次整批未处理'));const wrapper=open();try{await select(wrapper,rows());search.mockClear();await approve(wrapper);expect(wrapper.text()).toContain('选中订单已变化');expect(wrapper.findAll('button').some(b=>b.text()==='操作')).toBe(true);expect(search).not.toHaveBeenCalled()}finally{wrapper.unmount()}})
 it('does not send another command while the first batch is pending',async()=>{let resolve:any;api.auditPurchaseOrders.mockReturnValue(new Promise(r=>{resolve=r}));const wrapper=open();try{await select(wrapper,rows());await approve(wrapper);await approve(wrapper);expect(api.auditPurchaseOrders).toHaveBeenCalledTimes(1);resolve({code:10000});await flushPromises()}finally{wrapper.unmount()}})
 it('distinguishes a committed operation from a failed list refresh',async()=>{api.auditPurchaseOrders.mockResolvedValue({code:10000});const wrapper=open();try{await select(wrapper,rows());search.mockRejectedValue(new Error('QA refresh unavailable'));await approve(wrapper);expect(wrapper.text()).toContain('操作已提交，但列表刷新失败')}finally{wrapper.unmount()}})
})
