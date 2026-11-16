import {beforeEach,describe,expect,it,vi} from 'vitest'
const http=vi.hoisted(()=>({post:vi.fn()}))
vi.mock('@/plugins/http',()=>({useHttp:()=>http,DataUpType:{json:1}}))
import {PurchaseNoteAPI} from './index'
describe('reviewed procurement state commands',()=>{
 beforeEach(()=>vi.clearAllMocks())
 it('sends the displayed detail version without another read',()=>{PurchaseNoteAPI.check(['uuid-a'],true,'a'.repeat(64));expect(http.post).toHaveBeenCalledWith('/j3-purchase/purchase-note/verification',{ids:['uuid-a'],type:1,version:'a'.repeat(64)})})
 it('sends every batch member and its displayed version',()=>{const versions={a:'a'.repeat(64),b:'b'.repeat(64)};PurchaseNoteAPI.audit(['a','b'],false,versions);expect(http.post).toHaveBeenCalledWith('/j3-purchase/purchase-note/audit',{ids:['a','b'],type:0,versions})})
 it('rejects missing, duplicate or incomplete selections before any submission',()=>{for(const ids of [['a',''],['a','a'],['a','b']])expect(()=>PurchaseNoteAPI.check(ids,true,{a:'a'.repeat(64)})).toThrow();expect(http.post).not.toHaveBeenCalled()})
 it('rejects missing, malformed and extra versions',()=>{for(const value of [undefined,'old',{}, {a:'a'.repeat(64),extra:'b'.repeat(64)}])expect(()=>PurchaseNoteAPI.audit(['a'],true,value as any)).toThrow();expect(http.post).not.toHaveBeenCalled()})
})
