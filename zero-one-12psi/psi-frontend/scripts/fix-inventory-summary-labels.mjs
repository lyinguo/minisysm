import fs from 'fs'

const p =
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptSummary.vue'
let s = fs.readFileSync(p, 'utf8')
s = s.replace(/label="其它入库[^"]*align="/g, 'label="其它入库单" align="')
s = s.replace(/label="其它出库[^"]*align="/g, 'label="其它出库单" align="')
fs.writeFileSync(p, s, 'utf8')
console.log('ok')
