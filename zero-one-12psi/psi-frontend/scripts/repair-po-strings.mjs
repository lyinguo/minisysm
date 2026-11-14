import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const file = path.join(path.dirname(fileURLToPath(import.meta.url)), '../src/views/report/purchase/PurchaseOrder.vue')
let s = fs.readFileSync(file, 'utf8')
s = s.replace(/加载采购订单跟踪表失[^']*\)/g, "加载采购订单跟踪表失败')")
s = s.replace(/设置默认排序.单据排序"/g, '设置默认排序为"单据排序"')
fs.writeFileSync(file, s, 'utf8')
console.log('PurchaseOrder strings fixed')
