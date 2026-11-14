import fs from 'fs'

for (const rel of [
  'purchase/PurchaseList.vue',
  'sales/SaleList.vue'
]) {
  const p = `D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/${rel}`
  let s = fs.readFileSync(p, 'utf8')
  s = s.replace(/<span class="date-separator">[\s\S]*?<\/span>/g, '<span class="date-separator">至</span>')
  s = s.replace(/<span class="date-separator">[^<]*\/span>/g, '<span class="date-separator">至</span>')
  fs.writeFileSync(p, s)
  console.log('fixed', rel)
}
