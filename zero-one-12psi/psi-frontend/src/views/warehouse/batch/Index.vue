<!--
 * @Description: 仓库管理-批次查询主页面
-->
<template>
  <div class="stock area">
    <div class="layout">
      <SearchPopover @search="handleSearch" />
      <el-button-group>
        <el-button @click="handleExport">导出</el-button>
        <el-button @click="handleReload">刷新</el-button>
      </el-button-group>
    </div>
    <el-divider />

    <NormalTable
      :tabdata="tablePageData"
      :taboperbtns="tableOperBtns"
      :istabexpand="false"
      :istabmultiple="false"
      :tabattr="tableAttr"
      @page-change="handlePageChange"
      @taboper-click="handleTableOperClick"
    >
      <template #columns>
        <el-table-column prop="name" label="商品名称" width="220px" fixed="left" />
        <el-table-column prop="totalStock" label="库存数量" width="120px" />
        <el-table-column label="仓库">
          <template v-for="column in tableColumn" :key="column.key">
            <el-table-column :prop="column.key" :label="column.name" width="90px" />
          </template>
        </el-table-column>
        <el-table-column prop="protect" label="保质期(天)" width="120px" />
        <el-table-column prop="startTime" label="生产日期" width="160px" />
        <el-table-column prop="endTime" label="过期日期" width="160px" />
        <el-table-column prop="number" label="商品编号" width="160px" />
        <el-table-column prop="spec" label="规格型号" width="160px" />
        <el-table-column prop="categoryName" label="商品分类" width="120px" />
        <el-table-column prop="brand" label="商品品牌" width="120px" />
        <el-table-column prop="unit" label="商品单位" width="120px" />
        <el-table-column prop="code" label="商品条码" width="160px" />
        <el-table-column prop="data" label="商品备注" width="160px" />

        <el-table-column label="相关操作" min-width="120px" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="showBatchDetail(scope.row)">详情</el-button>
          </template>
        </el-table-column>
      </template>

      <template #customercell="{ prop, row }">
        <template v-if="tableColumn.some((col) => col.key === prop)">
          <template v-if="row.children && row.children.length > 0">
            <span>-</span>
          </template>
          <template v-else>
            {{ row[prop] ?? '-' }}
          </template>
        </template>
        <template v-else-if="prop === 'name' && row.level === 'attr'">
          <span style="color: #909399">└─ {{ row.name }}</span>
        </template>
        <template v-else-if="prop === 'name' && row.level === 'batch'">
          <span style="color: #606266">{{ row.batchNumber || row.name }}</span>
        </template>
        <template v-else>
          {{ row[prop] ?? '-' }}
        </template>
      </template>
    </NormalTable>

    <DetailDialog
      v-model:visible="batchDetailDialog.visible"
      :batch-data="batchDetailDialog.batchData"
      @closed="handleDetailDialogClose"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import NormalTable from '@/components/normaltable/NormalTable.vue'
import type { MyTableOperationsBtn, PageDTO } from '@/components/normaltable/type'
import SearchPopover from './SearchPopover.vue'
import DetailDialog from './DetailDialog.vue'
import { getBatchList, exportBatchExcel } from '@/apis/warehouse/batch/index'
import type {
  BatchDTO,
  BatchNumberDTO,
  BatchAttrDTO,
  BatchDocumentDTO,
  BatchListRequest,
  WarehouseStockDTO
} from '@/apis/warehouse/batch/type'

interface TableColumn {
  key: string
  name: string
}

const tableColumn = ref<TableColumn[]>([])

const batchDetailDialog = reactive({
  visible: false,
  batchData: null as any
})

const tablePageData = reactive<PageDTO<any>>({
  rows: [],
  total: 0,
  pageIndex: 1,
  pageSize: 30
})

const searchFrom = ref<BatchListRequest>({})

const tableAttr = reactive({
  'row-key': 'key',
  'tree-props': { children: 'children' },
  'header-cell-style': { textAlign: 'center', backgroundColor: '#f5f7fa' },
  'cell-style': { textAlign: 'center' }
})

const tableOperBtns = ref<MyTableOperationsBtn[]>([
  { text: '详情', evtname: 'detail', attr: { size: 'small', type: 'primary' } }
])

function applyWarehouseColumns(row: Record<string, any>, warehouses?: WarehouseStockDTO[]) {
  warehouses?.forEach((wh) => {
    if (wh.warehouseId) {
      row[wh.warehouseId] = wh.stockNum
    }
  })
}

function mapBatchDocumentsToWarehouse(batchRow: Record<string, any>, documents?: BatchDocumentDTO[]) {
  documents?.forEach((doc) => {
    // 批次明细按仓库名称展示在动态列上较难映射，保留总库存即可
    if (doc.nums != null && batchRow.totalStock == null) {
      batchRow.totalStock = doc.nums
    }
  })
}

function buildBatchRow(item: BatchDTO, batch: BatchNumberDTO, attrName = '') {
  const firstDoc = batch.batchDocuments?.[0]
  const batchRow: Record<string, any> = {
    key: `batch_${firstDoc?.batchId || item.id}_${batch.batchNumber}`,
    level: 'batch',
    id: firstDoc?.batchId,
    batchId: firstDoc?.batchId,
    goodsId: item.id,
    batchNumber: batch.batchNumber,
    name: attrName ? `${attrName} / ${batch.batchNumber}` : batch.batchNumber,
    totalStock: batch.totalStock,
    number: item.number,
    spec: item.spec,
    brand: item.brand,
    categoryName: item.categoryName,
    unit: item.unit,
    code: item.code,
    data: item.data,
    protect: item.protect,
    startTime: firstDoc?.productDate || '-',
    endTime: firstDoc?.expireDate || '-',
    batchDocuments: batch.batchDocuments || [],
    batchIds: collectBatchIdsFromNumber(batch)
  }
  mapBatchDocumentsToWarehouse(batchRow, batch.batchDocuments)
  return batchRow
}

function collectBatchIdsFromNumber(batch: BatchNumberDTO): string[] {
  const ids = new Set<string>()
  batch.batchDocuments?.forEach((doc) => {
    if (doc.batchId) ids.add(doc.batchId)
  })
  return Array.from(ids)
}

function collectBatchIdsFromGoods(item: BatchDTO): string[] {
  const ids = new Set<string>()
  item.noAttrBatches?.forEach((batch) => {
    collectBatchIdsFromNumber(batch).forEach((id) => ids.add(id))
  })
  item.attrBatches?.forEach((attr) => {
    attr.batches?.forEach((batch) => {
      collectBatchIdsFromNumber(batch).forEach((id) => ids.add(id))
    })
  })
  return Array.from(ids)
}

const processBatchData = (data: BatchDTO[]) => {
  return data.map((item) => {
    const processedItem: Record<string, any> = {
      ...item,
      key: `goods_${item.id}`,
      level: 'goods',
      batchIds: collectBatchIdsFromGoods(item),
      children: [] as Record<string, any>[]
    }

    applyWarehouseColumns(processedItem, item.goodsWarehouses)

    if (item.attrBatches && item.attrBatches.length > 0) {
      processedItem.children = item.attrBatches.map((attr: BatchAttrDTO) => {
        const attrRow: Record<string, any> = {
          key: `attr_${item.id}_${attr.attrName}`,
          level: 'attr',
          name: attr.attrName,
          totalStock: attr.attrStock,
          number: item.number,
          spec: item.spec,
          brand: item.brand,
          categoryName: item.categoryName,
          unit: item.unit,
          code: item.code,
          data: item.data,
          protect: item.protect,
          children: (attr.batches || []).map((batch) => buildBatchRow(item, batch, attr.attrName || ''))
        }
        return attrRow
      })
    } else {
      processedItem.children = (item.noAttrBatches || []).map((batch) => buildBatchRow(item, batch))
    }

    if (processedItem.children.length === 0) {
      processedItem.startTime = '-'
      processedItem.endTime = '-'
    } else if (!item.attrBatches?.length) {
      const first = processedItem.children[0]
      processedItem.startTime = first.startTime
      processedItem.endTime = first.endTime
    }

    return processedItem
  })
}

function showBatchDetail(row: any) {
  const batchIds: string[] =
    row.batchIds?.length > 0
      ? row.batchIds
      : row.batchId
        ? [row.batchId]
        : []

  if (batchIds.length === 0) {
    ElMessage.warning('该商品暂无批次流水，请先做其它入库/采购入库生成批次')
    return
  }

  batchDetailDialog.batchData = {
    batchIds,
    goodsId: row.goodsId || row.id,
    name: row.name,
    number: row.number,
    batchNumber: row.batchNumber,
    spec: row.spec,
    categoryName: row.categoryName,
    brand: row.brand,
    unit: row.unit,
    code: row.code,
    data: row.data,
    totalStock: row.totalStock,
    protect: row.protect,
    startTime: row.startTime,
    endTime: row.endTime
  }
  batchDetailDialog.visible = true
}

function handleDetailDialogClose() {
  batchDetailDialog.visible = false
  batchDetailDialog.batchData = null
}

async function fetchBatchData(): Promise<void> {
  try {
    const params: BatchListRequest = {
      pageIndex: tablePageData.pageIndex,
      pageSize: tablePageData.pageSize,
      ...searchFrom.value
    }

    Object.keys(params).forEach((key) => {
      const paramKey = key as keyof BatchListRequest
      const value = params[paramKey]
      if (
        value === '' ||
        value === null ||
        value === undefined ||
        (Array.isArray(value) && value.length === 0)
      ) {
        delete params[paramKey]
      }
    })

    await getBatchList(
      params,
      (data) => {
        tablePageData.rows = processBatchData(data.rows || [])
        tablePageData.total = data.total || 0
        extractWarehouseColumns(data.rows || [])
      },
      (error) => {
        ElMessage.warning((error as any)?.message || '获取批次数据失败')
      }
    )
  } catch (error) {
    ElMessage.error('服务器响应超时!')
    console.error('Error fetching batch data:', error)
  }
}

function extractWarehouseColumns(data: BatchDTO[]) {
  const warehouseMap = new Map<string, TableColumn>()
  data.forEach((item) => {
    item.goodsWarehouses?.forEach((wh) => {
      if (wh.warehouseId && wh.warehouseName) {
        warehouseMap.set(wh.warehouseId, {
          key: wh.warehouseId,
          name: wh.warehouseName
        })
      }
    })
  })
  tableColumn.value = Array.from(warehouseMap.values())
}

function handleSearch(params: BatchListRequest) {
  searchFrom.value = { ...params }
  tablePageData.pageIndex = params.pageIndex || 1
  if (params.pageSize) tablePageData.pageSize = params.pageSize
  fetchBatchData()
}

function handlePageChange(data: PageDTO<any>): void {
  Object.assign(tablePageData, data)
  fetchBatchData()
}

function handleTableOperClick(_index: number, row: any, evtname: string): void {
  if (evtname === 'detail') showBatchDetail(row)
}

function downloadBlob(blobData: Blob, title: string) {
  const filename = `${title}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`
  const blob = new Blob([blobData], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

function handleExport(): void {
  const exportParams: BatchListRequest = { ...searchFrom.value }
  Object.keys(exportParams).forEach((key) => {
    const paramKey = key as keyof BatchListRequest
    const value = exportParams[paramKey]
    if (
      value === '' ||
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length === 0)
    ) {
      delete exportParams[paramKey]
    }
  })

  ElMessage.info('正在导出数据...')
  exportBatchExcel(
    exportParams,
    (blob) => downloadBlob(blob, '批次列表'),
    (error) => {
      ElMessage.error(
        (error instanceof Error && error.message) || (error as any)?.message || '导出失败'
      )
    }
  )
}

function handleReload(): void {
  fetchBatchData()
  ElMessage.success('页面刷新成功!')
}

onMounted(() => {
  fetchBatchData()
})
</script>

<style scoped>
.layout {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
:deep(.el-table .el-table__header-wrapper .el-table__header .el-table__cell:first-child),
:deep(.el-table .el-table__body-wrapper .el-table__body .el-table__cell:first-child) {
  text-align: left !important;
}
</style>
