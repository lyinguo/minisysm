import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

for (const rel of [
  'src/views/report/purchase/PurchaseSummary.vue',
  'src/views/report/sales/SaleSummary.vue'
]) {
  const file = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', rel)
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(
    /placeholder="单据开始日期""YYYY-MM-DD"/g,
    'placeholder="单据开始日期"\n                    value-format="YYYY-MM-DD"'
  )
  s = s.replace(
    /placeholder="单据结束日期""/g,
    'placeholder="单据结束日期"\n                    value-format="YYYY-MM-DD"'
  )
  fs.writeFileSync(file, s, 'utf8')
  console.log('fixed date pickers:', rel)
}
