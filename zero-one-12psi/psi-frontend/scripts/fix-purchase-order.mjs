import fs from 'fs'

const filePath = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseOrder.vue'
let content = fs.readFileSync(filePath, 'utf8')

content = content.replace(
  /(\} catch \(error: unknown\) \{\s+originalTableData\.value = \[\]\s+currentTableData\.value = \[\]\s+ElMessage\.error\(error instanceof Error \? error\.message : '加载采购订单跟踪表失败'\))\s*\n\s*\/\/ 搜索表单数据[^\n]*\nconst searchFormData/,
  `$1
  } finally {
    loading.value = false
  }
}

// 原始表格数据
const originalTableData = ref<any[]>([])

// 当前显示的表格数据
const currentTableData = ref<any[]>([])

// 搜索表单数据 - 设置默认排序为"单据排序"
const searchFormData`
)

fs.writeFileSync(filePath, content, 'utf8')
console.log('PurchaseOrder.vue fixed')
