import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue'
let s = fs.readFileSync(file, 'utf8')

s = s.replace(
  /tableData\.value = list\.map\(\(item: any, index: number\) => \(\{[\s\S]*?\}\)\)/,
  `tableData.value = list.map((item: any, index: number) => ({
      id: item.id ?? index,
      productName: item.productName ?? '',
      auxiliaryAttr: item.auxiliaryAttribute ?? '',
      productCode:
        item.productNumber !== undefined && item.productNumber !== null
          ? String(item.productNumber)
          : '',
      specification: item.specificationModel ?? '',
      unit: item.unit ?? '',
      quantity: Number(item.quantity ?? 0),
      discount: Number(item.discountAmount ?? 0),
      tax: Number(item.taxAmount ?? 0),
      totalWithTax: Number(item.totalAmountWithTax ?? 0),
      cost: Number(item.cost ?? 0),
      totalCost: Number(item.totalCost ?? 0),
      grossProfit: Number(item.grossProfit ?? 0),
      grossProfitMargin: Number(item.grossProfitMargin ?? 0)
    }))`
)

fs.writeFileSync(file, s, 'utf8')
console.log('SaleList map fixed')
