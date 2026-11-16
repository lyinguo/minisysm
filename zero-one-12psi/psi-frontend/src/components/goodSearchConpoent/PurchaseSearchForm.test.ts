import {it,expect,vi} from 'vitest'
import {shallowMount,flushPromises} from '@vue/test-utils'
const list=vi.hoisted(()=>vi.fn())
vi.mock('@/apis/purchase/PurchaseBooking/order',()=>({PurchaseOrderAPI:{getPurchaseOrderList:list}}))
vi.mock('./GoodSearchForm.vue',()=>({default:{name:'GoodSearchForm',template:'<div />'}}))
import Search from './PurchaseSearchForm.vue'
it('sends actual selected reference IDs and canonical numeric states',async()=>{list.mockResolvedValue({code:10000,data:{rows:[],total:0}});const wrapper=shallowMount(Search,{props:{pageIndex:1,pageSize:10}});try{await flushPromises();wrapper.findComponent({name:'GoodSearchForm'}).vm.$emit('search',{supplier:{id:'supplier-uuid',label:'供应商名称'},people:{value:'person-uuid',label:'人员名称'},user:{id:'actor-uuid',name:'制单人名称'},examine:2,state:4,goods:'商品甲',data:'备注'});await flushPromises();expect(list).toHaveBeenLastCalledWith(expect.objectContaining({supplier:'supplier-uuid',people:'person-uuid',user:'actor-uuid',examine:'1',state:'3',name:'商品甲',data:'备注'}))}finally{wrapper.unmount()}})
