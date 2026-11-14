import fs from 'fs'

const p =
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptSummary.vue'
let s = fs.readFileSync(p, 'utf8')

s = s.replace(
  /interface BillData \{[\s\S]*?interface TableRow \{[\s\S]*?\n\}/,
  `interface BillData {
  uct: number
  uns: number
  bct: number
}

interface TableRow {
  goodsData: GoodsData
  warehouseData: WarehouseData
  unit: string
  state: BillData
  buy: BillData
  bre: BillData
  sell: BillData
  sre: BillData
  swapOut: BillData
  swapEnter: BillData
  entry: BillData
  extry: BillData
  balance: BillData
}`
)

fs.writeFileSync(p, s, 'utf8')
console.log('interfaces fixed')
