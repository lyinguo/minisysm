import fs from 'fs'

function rebuildListTemplate(filePath, options) {
  const content = fs.readFileSync(filePath, 'utf8')
  const scriptIdx = content.indexOf('<script setup')
  const styleIdx = content.indexOf('<style', scriptIdx)
  if (scriptIdx === -1) throw new Error('no script in ' + filePath)

  const scriptAndStyle = content.slice(scriptIdx)
  const extraColumns = options.extraColumns || ''

  const template = `<template>
  <div class="sys area">
    <div class="operation-bar">
      <div class="operation-left">
        <el-popover
          placement="bottom-start"
          :width="400"
          trigger="click"
          v-model:visible="searchPopoverVisible"
        >
          <template #reference>
            <el-button class="search-btn">
              <el-icon><MoreFilled /></el-icon>
            </el-button>
          </template>
          <div class="search-popover">
            <div class="search-form">
              <div class="form-item">
                <el-input
                  v-model="searchForm.productName"
                  placeholder="请输入商品名称"
                  clearable
                />
              </div>
              <div class="form-item">
                <el-input
                  v-model="searchForm.productCode"
                  placeholder="请输入商品编号"
                  clearable
                />
              </div>
              <div class="form-item">
                <div class="date-range">
                  <el-date-picker
                    v-model="searchForm.orderStartDate"
                    type="date"
                    placeholder="开始日期"
                    style="width: 48%"
                    value-format="YYYY-MM-DD"
                  />
                  <span class="date-separator">至</span>
                  <el-date-picker
                    v-model="searchForm.orderEndDate"
                    type="date"
                    placeholder="结束日期"
                    style="width: 48%"
                    value-format="YYYY-MM-DD"
                  />
                </div>
              </div>
              <div class="form-actions">
                <el-button type="primary" @click="handleSearch" class="search-action-btn">
                  搜索
                </el-button>
                <el-button @click="handleResetSearch" class="reset-action-btn">重置</el-button>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
      <div class="operation-right">
        <el-button type="primary" @click="handleExport" class="action-btn">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="info" @click="handleResetSearch" class="action-btn">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-divider class="custom-divider" />

    <div class="table-container">
      <el-table
        :data="${options.tableData}"
        style="width: 100%"
        v-loading="loading"
        border
        class="grid-table"
      >
        <el-table-column prop="productName" label="商品名称" width="150" />
        <el-table-column prop="auxiliaryAttr" label="辅助属性" width="120" />
        <el-table-column prop="productCode" label="商品编号" width="120" />
        <el-table-column prop="specification" label="规格型号" width="120" />
        <el-table-column prop="unit" label="单位" width="80" align="center" />
        <el-table-column prop="quantity" label="数量" width="100" align="right" />
        <el-table-column prop="discount" label="折扣额" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.discount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="tax" label="税额" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.tax) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="totalWithTax" label="价税合计" width="120" align="right">
          <template #default="scope">
            <span class="total-highlight">{{ formatCurrency(scope.row.totalWithTax) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="totalCost" label="总成本" width="120" align="right">
          <template #default="scope">
            <span class="total-cost-highlight">{{ formatCurrency(scope.row.totalCost) }}</span>
          </template>
        </el-table-column>${extraColumns}
      </el-table>

      <div class="pagination-container pagination-left">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 30, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

`

  fs.writeFileSync(filePath, template + scriptAndStyle, 'utf8')
  console.log('rebuilt template:', filePath)
}

rebuildListTemplate(
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseList.vue',
  { tableData: 'tableData' }
)

rebuildListTemplate(
  'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue',
  {
    tableData: 'filteredTableData',
    extraColumns: `
        <el-table-column prop="grossProfit" label="毛利润" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.grossProfit) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grossProfitMargin" label="毛利率" width="100" align="right">
          <template #default="scope">
            <span>{{ (scope.row.grossProfitMargin * 100).toFixed(2) }}%</span>
          </template>
        </el-table-column>`
  }
)
