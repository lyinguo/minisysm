import fs from 'fs'

const p = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleSummary.vue'
let s = fs.readFileSync(p, 'utf8')
s = s.replace(
  /const handleFilterTypeChange = \(\) => \{\s*\/\/[^\n]*if \(searchForm\.filterType !== 'customer'\)/,
  "const handleFilterTypeChange = () => {\n  if (searchForm.filterType !== 'customer')"
)
fs.writeFileSync(p, s, 'utf8')
console.log('ok')
