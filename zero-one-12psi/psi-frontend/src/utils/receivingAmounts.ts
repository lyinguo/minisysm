/** Match the server's positive HALF_UP arithmetic at four decimal places. */
export function receivingAmounts(price:number,quantity:number,discount:number,tax:number) {
  if(discount>100 || tax>100)throw new Error('折扣或税率无效')
  const scaled=(value:number,precision:number)=>{
    if(!Number.isFinite(value) || value<0)throw new Error('金额或数量无效')
    return BigInt(value.toFixed(precision).replace('.',''))
  }
  const divide=(value:bigint,divisor:bigint)=>(value+divisor/BigInt(2))/divisor
  const scale=BigInt(10000)
  const gross=divide(scaled(price,4)*scaled(quantity,4),scale)
  const net=gross-divide(gross*scaled(discount,2),scale)
  const actual=net+divide(net*scaled(tax,2),scale)
  return {net:Number(net)/10000,actual:Number(actual)/10000}
}
