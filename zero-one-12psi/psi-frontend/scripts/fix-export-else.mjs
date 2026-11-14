import fs from 'fs'

const files = [
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue',
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseList.vue'
]

for (const file of files) {
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(
    /\} else \{\s*\/\/[^\n]*blob = new Blob/g,
    '} else {\n      blob = new Blob'
  )
  fs.writeFileSync(file, s, 'utf8')
  console.log('fixed', file.split('/').pop())
}
