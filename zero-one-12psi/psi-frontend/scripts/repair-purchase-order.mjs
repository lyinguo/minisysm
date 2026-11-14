import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')

// Fix Summary template options
for (const rel of [
  'src/views/report/purchase/PurchaseSummary.vue',
  'src/views/report/sales/SaleSummary.vue'
]) {
  const file = path.join(root, rel)
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/placeholder="请选择筛选类[^\n"]*/g, 'placeholder="请选择筛选类型"')
  s = s.replace(/<el-option label="按商品 value="product" \/>/g, '<el-option label="按商品" value="product" />')
  s = s.replace(/<el-option label="按客[^"]* value="customer" \/>/g, '<el-option label="按客户" value="customer" />')
  s = s.replace(/<el-option label="按供应商" value="supplier" \/>/g, '<el-option label="按供应商" value="supplier" />')
  s = s.replace(/<el-option label="按用[^"]* value="user" \/>/g, '<el-option label="按用户" value="user" />')
  s = s.replace(/<el-option label="按人[^"]* value="person" \/>/g, '<el-option label="按人员" value="person" />')
  fs.writeFileSync(file, s, 'utf8')
  console.log('fixed template:', rel)
}

// Fix PurchaseOrder.vue script block
const poFile = path.join(root, 'src/views/report/purchase/PurchaseOrder.vue')
let po = fs.readFileSync(poFile, 'utf8')

const replacement = `// 将原始数据转换为商品排序模式的数据结构
const transformToProductStructure = (data: any[]) => {
  const allChildren: any[] = []
  data.forEach((parent) => {
    if (parent.children && parent.children.length > 0) {
      parent.children.forEach((child: any) => {
        allChildren.push({ ...child })
      })
    }
  })

  const productGroups: { [key: string]: any[] } = {}

  allChildren.forEach((child) => {
    const key = \`\${child.productName}_\${child.auxiliaryAttr}_\${child.warehouse}\`
    if (!productGroups[key]) {
      productGroups[key] = []
    }
    productGroups[key].push(child)
  })

  const productData = Object.entries(productGroups).map(([, children], index) => {
    const firstChild = children[0]
    return {
      id: \`product_\${index + 1}\`,
      productName: firstChild.productName,
      auxiliaryAttr: firstChild.auxiliaryAttr,
      warehouse: firstChild.warehouse,
      isChild: false,
      children: children.map((child, childIndex) => ({
        ...child,
        id: \`product_\${index + 1}_child_\${childIndex + 1}\`,
        productName: firstChild.productName,
        auxiliaryAttr: firstChild.auxiliaryAttr,
        warehouse: firstChild.warehouse,
        isChild: true
      }))
    }
  })

  return productData.sort((a, b) => a.productName.localeCompare(b.productName, 'zh-CN'))
}

// 刷新功能
const handleRefresh = () => {
  if (goodSearchRef.value) {
    goodSearchRef.value.resetForm()
  }
  Object.assign(searchFormData, {
    goods: '',
    number: '',
    supplier: '',
    startTime: '',
    endTime: '',
    startArrival: '',
    endArrival: '',
    warehouse: '',
    sortType: '单据排序'
  })
  loadData()
  ElMessage.success('已刷新数据')
}

// 导出功能实现
const handleExport = async () => {
  try {
    const res = await purchaseOrderTrackingFormOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, \`采购订单跟踪表_\${new Date().toISOString().split('T')[0]}.xlsx\`)
    ElMessage.success('导出成功')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

`

po = po.replace(
  /\/\/ 将原始数据转换为商品排序模式的数据结构[\s\S]*?\/\/ 分页相关/,
  replacement + '// 分页相关'
)
fs.writeFileSync(poFile, po, 'utf8')
console.log('fixed PurchaseOrder.vue script')
