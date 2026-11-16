import {it,expect,vi} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import ElementPlus from 'element-plus'
vi.mock('./Supplier.vue',()=>({default:{template:'<div />'}}))
vi.mock('./Customer.vue',()=>({default:{template:'<div />'}}))
vi.mock('./Warehouse.vue',()=>({default:{template:'<div />'}}))
vi.mock('./Account.vue',()=>({default:{template:'<div />'}}))
vi.mock('./PeopleList.vue',()=>({default:{template:'<div />'}}))
vi.mock('./UserList.vue',()=>({default:{template:'<div />'}}))
import GoodSearch from './GoodSearchForm.vue'
it('explicit filter button opens, closes and reopens the controlled popover',async()=>{const wrapper=mount(GoodSearch,{props:{config:{inline:false,showNumber:true,showSupplier:false,showCustomer:false,showWarehouse:false,showAccount:false,showPeople:false,showUser:false,showBillDate:false,showArrivalDate:false,showGoods:false,showExamine:false,showState:false}},global:{plugins:[ElementPlus]},attachTo:document.body});try{const button=wrapper.find('button[aria-label="展开筛选条件"]');await button.trigger('click');await flushPromises();expect(button.attributes('aria-expanded')).toBe('true');expect(wrapper.find('input[placeholder="请输入单据编号"]').exists()).toBe(true);await wrapper.findAll('button').find(b=>b.text()==='关闭')!.trigger('click');await flushPromises();expect(button.attributes('aria-expanded')).toBe('false');await button.trigger('click');await flushPromises();expect(button.attributes('aria-expanded')).toBe('true')}finally{wrapper.unmount()}})
