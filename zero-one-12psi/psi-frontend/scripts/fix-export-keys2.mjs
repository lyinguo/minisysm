import fs from 'fs'

const files = [
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/fund/CurrentAccount.vue',
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/fund/CustomerStatement.vue',
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/fund/SupplierStatement.vue'
]

for (const file of files) {
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/'制单.{0,3}: row/g, "'制单人': row")
  s = s.replace(/'属.{0,3}: /g, "'属性': ")
  s = s.replace(/'折扣.{0,3}: /g, "'折扣额': ")
  fs.writeFileSync(file, s, 'utf8')
  console.log('fixed', file.split('/').pop())
}
