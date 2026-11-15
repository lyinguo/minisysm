import {beforeEach,describe,expect,it,vi} from 'vitest'
import {shallowMount,flushPromises} from '@vue/test-utils'
import {ElMessage,ElMessageBox} from 'element-plus'
const api=vi.hoisted(()=>({deletePurchaseOrders:vi.fn(),importTemplate:vi.fn()}))
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:api}))
vi.mock('@/components/goodSearchConpoent',()=>({PurchaseSearchForm:{template:'<div />'}}))
vi.mock('./PurchaseBookDetailDialog.vue',()=>({default:{template:'<div />'}}))
vi.mock('@/components/operationbuttons/OperationButtons.vue',()=>({default:{template:'<div />'}}))
import Form from './PurchaseBookForm.vue'

function open(){return shallowMount(Form,{global:{stubs:{ElButton:{template:'<button @click="$emit(\'click\')"><slot /></button>'},ElTable:{name:'ElTable',template:'<div />'},OperationButtons:true,PurchaseBookDetailDialog:true}}})}
describe('order batch deletion result',()=>{
 beforeEach(()=>{vi.restoreAllMocks();api.deletePurchaseOrders.mockReset();vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as any);vi.spyOn(ElMessage,'error').mockImplementation(()=>({close(){}}) as any);vi.spyOn(ElMessage,'success').mockImplementation(()=>({close(){}}) as any)})
 it('keeps selection and reports server refusal without claiming success',async()=>{const wrapper=open();try{wrapper.findComponent({name:'ElTable'}).vm.$emit('selection-change',[{id:'real-order'}]);await flushPromises();api.deletePurchaseOrders.mockResolvedValue({code:9995,message:'已有收货单，不能删除'});await wrapper.findAll('button').find(b=>b.text()==='删除')!.trigger('click');await flushPromises();expect(api.deletePurchaseOrders).toHaveBeenCalledWith(['real-order']);expect(ElMessage.error).toHaveBeenCalledWith('已有收货单，不能删除');expect(ElMessage.success).not.toHaveBeenCalled();expect(wrapper.findAll('button').some(b=>b.text()==='删除')).toBe(true)}finally{wrapper.unmount()}})
 it('does not partially delete a selection containing missing IDs',async()=>{const wrapper=open();try{wrapper.findComponent({name:'ElTable'}).vm.$emit('selection-change',[{id:'real-order'},{}]);await flushPromises();await wrapper.findAll('button').find(b=>b.text()==='删除')!.trigger('click');await flushPromises();expect(api.deletePurchaseOrders).not.toHaveBeenCalled();expect(ElMessage.error).toHaveBeenCalledWith('选中的单据包含无效订单ID，请刷新列表后重新选择')}finally{wrapper.unmount()}})
})
