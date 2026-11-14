import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue'
let s = fs.readFileSync(file, 'utf8')

s = s.replace(
  /interface SalesRankingRow \{[\s\S]*?\n\}\n\ninterface SearchForm/,
  `interface SalesRankingRow {
  id?: number | string
  productName: string
  auxiliaryAttr: string
  productCode: string
  specification: string
  unit: string
  quantity: number
  discount: number
  tax: number
  totalWithTax: number
  cost: number
  totalCost: number
  grossProfit: number
  grossProfitMargin: number
}

interface SearchForm`
)

fs.writeFileSync(file, s, 'utf8')
console.log('SaleList interface fixed')
