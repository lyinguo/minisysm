<!--
 * 仓库管理-序列查询
-->
<template>
  <div class="serial-page">
    <div class="toolbar">
      <el-input
        v-model="query.serialNumber"
        clearable
        placeholder="序列号"
        style="width: 160px"
        @keyup.enter="loadList(1)"
      />
      <el-input
        v-model="query.goodsName"
        clearable
        placeholder="商品名称"
        style="width: 160px"
        @keyup.enter="loadList(1)"
      />
      <el-input
        v-model="query.goodsNumber"
        clearable
        placeholder="商品编号"
        style="width: 140px"
        @keyup.enter="loadList(1)"
      />
      <el-select v-model="query.state" clearable placeholder="状态" style="width: 120px">
        <el-option label="未销售" :value="0" />
        <el-option label="已销售" :value="1" />
        <el-option label="已调拨" :value="2" />
        <el-option label="已退货" :value="3" />
      </el-select>
      <el-button type="primary" :loading="loading" @click="loadList(1)">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe style="width: 100%; margin-top: 12px">
      <el-table-column type="index" label="#" width="60" align="center" />
      <el-table-column prop="serialNumber" label="序列号" min-width="160" />
      <el-table-column prop="goodsName" label="商品名称" min-width="160" />
      <el-table-column prop="goodsNumber" label="商品编号" min-width="120" />
      <el-table-column prop="goodsSpec" label="规格型号" min-width="120" />
      <el-table-column prop="warehouseName" label="仓库" min-width="120" />
      <el-table-column prop="stateLabel" label="状态" width="100" align="center" />
    </el-table>

    <div class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next, sizes"
        :total="total"
        v-model:current-page="query.pageIndex"
        v-model:page-size="query.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="(p: number) => loadList(p)"
        @size-change="() => loadList(1)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSerialList, type SerialRow } from '@/apis/warehouse/serial'

const loading = ref(false)
const rows = ref<SerialRow[]>([])
const total = ref(0)
const query = reactive({
  pageIndex: 1,
  pageSize: 20,
  serialNumber: '',
  goodsName: '',
  goodsNumber: '',
  state: null as number | null
})

async function loadList(page = query.pageIndex) {
  query.pageIndex = page
  loading.value = true
  try {
    const res = await getSerialList({ ...query })
    rows.value = res.data?.rows || []
    total.value = res.data?.total || 0
  } catch (error) {
    rows.value = []
    total.value = 0
    ElMessage.error(error instanceof Error ? error.message : '序列查询失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  query.serialNumber = ''
  query.goodsName = ''
  query.goodsNumber = ''
  query.state = null
  loadList(1)
}

onMounted(() => loadList(1))
</script>

<style scoped>
.serial-page {
  padding: 16px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
