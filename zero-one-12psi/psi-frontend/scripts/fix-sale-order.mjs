import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleOrder.vue'
let s = fs.readFileSync(file, 'utf8')

const start = s.indexOf('const prepareExportData = () => {')
const end = s.indexOf('// 分页相关', start)
if (start === -1 || end === -1) {
  // try alternate marker
  const end2 = s.indexOf('const currentPage = ref(1)', start)
  if (start !== -1 && end2 !== -1) {
    s = s.slice(0, start) + s.slice(end2)
    fs.writeFileSync(file, s, 'utf8')
    console.log('removed via currentPage marker')
  } else {
    console.log('markers not found', start, end, end2)
  }
} else {
  s = s.slice(0, start) + s.slice(end)
  fs.writeFileSync(file, s, 'utf8')
  console.log('removed via pagination comment')
}

console.log('still has prepareExportData:', s.includes('prepareExportData'))
