import {describe,expect,it} from 'vitest'
import {receivingAmounts} from './receivingAmounts'
describe('receiving decimal preview',()=>{
 it('matches exact half-up rather than rounding a binary floating point product',()=>{expect(receivingAmounts(1.0001,.5,0,0)).toEqual({net:.5001,actual:.5001})})
 it('rounds gross, discount and tax at the same four-decimal stages as the server',()=>{expect(receivingAmounts(1.125,1.25,12.5,13)).toEqual({net:1.2305,actual:1.3905});expect(receivingAmounts(100,1,10,13)).toEqual({net:90,actual:101.7})})
})
