import fs from 'fs'

// CurrentAccount export key
{
  const p = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/fund/CurrentAccount.vue'
  let s = fs.readFileSync(p, 'utf8')
  s = s.replace(/'制单[^']*': row\.sourceData/g, "'制单人': row.sourceData")
  fs.writeFileSync(p, s, 'utf8')
  console.log('CurrentAccount fixed')
}

// InventoryReceiptSummary export + loadData
{
  const p =
    'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptSummary.vue'
  let s = fs.readFileSync(p, 'utf8')

  s = s.replace(
    /'汇总-成本': row\.balance\?\.uct \|\| 0,\s*'汇总-数量': row\.balance\?\.uns \|\| 0,\s*'汇总-成本': unknown\) \{[\s\S]*?loading\.value = false\n  \}\n\}/,
    `'汇总-成本': row.balance?.uct || 0,
    '汇总-数量': row.balance?.uns || 0,
    '汇总-总成本': row.balance?.bct || 0
  }))
})

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const res = await WarehouseReportAPI.summaryList(buildSummaryParams())
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows as TableRow[]
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载收发汇总失败')
  } finally {
    loading.value = false
  }
}`
  )

  fs.writeFileSync(p, s, 'utf8')
  console.log('InventoryReceiptSummary fixed')
}
