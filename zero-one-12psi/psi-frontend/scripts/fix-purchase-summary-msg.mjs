import fs from 'fs'

const p = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseSummary.vue'
const lines = fs.readFileSync(p, 'utf8').split('\n')
lines[731] = '  ElMessage.success(`搜索完成，${searchInfo}`)'
fs.writeFileSync(p, lines.join('\n'), 'utf8')
console.log('fixed:', lines[731])
