import fs from 'fs'

const p =
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptSummary.vue'
let s = fs.readFileSync(p, 'utf8')
s = s.replace(/label="调拨[^"]*align="/g, 'label="调拨单-出" align="')
s = s.replace(/<!-- 调拨[^>]*-->/g, '<!-- 调拨单-出 -->')
fs.writeFileSync(p, s, 'utf8')
console.log('ok')
