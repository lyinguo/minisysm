import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseDetail.vue'
let s = fs.readFileSync(file, 'utf8')

s = s.replace(/searchFormData\.orderType === '采购.+ t = 1/g, "searchFormData.orderType === '采购单') t = 1")
s = s.replace(/'采购退货单' : '采购.+?,/g, "'采购退货单' : '采购单',")
s = s.replace(/item\.orderType === '采购.+\)/g, "item.orderType === '采购单')")

fs.writeFileSync(file, s, 'utf8')
console.log('done', s.includes("'采购?)"))
