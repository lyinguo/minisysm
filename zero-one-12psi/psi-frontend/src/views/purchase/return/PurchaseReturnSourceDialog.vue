<template>
  <el-dialog :model-value="modelValue" title="采购退货来源预览" width="min(1200px,96vw)" :close-on-click-modal="false" @update:model-value="$emit('update:modelValue', $event)">
    <el-alert title="这里只核对退货来源，尚未生成退货单，不会出库或记录供应商退款。来源可退数量与当前库存不同，提交退货时需再次核对。" type="info" :closable="false" show-icon />
    <p v-if="loading" role="status">正在读取原采购单及可退信息…</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="source && !loading && !error">
      <p>来源采购单：{{ source.sourceNumber }}　原供应商：{{ source.supplierName || source.supplier }}</p>
      <el-table :data="source.items" border max-height="420" aria-label="原采购单可退明细">
        <el-table-column prop="goodsName" label="来源商品" min-width="160" />
        <el-table-column prop="warehouseName" label="原入库仓库" min-width="130" />
        <el-table-column prop="unit" label="单位" width="75" />
        <el-table-column prop="sourceQuantity" label="原采购数" width="90" />
        <el-table-column prop="returned" label="已审核退货" width="100" />
        <el-table-column prop="reserved" label="草稿占用" width="95" />
        <el-table-column prop="available" label="来源可退" width="100" />
        <el-table-column label="当前库存" min-width="120"><template #default="{ row }">{{ row.service ? '服务不计仓库库存' : row.stockQuantity }}</template></el-table-column>
        <el-table-column prop="price" label="来源单价" width="105" />
        <el-table-column label="预计价税合计" width="125"><template #default="{ row }">{{ Number(row.tpt).toFixed(4) }}</template></el-table-column>
      </el-table>
      <div v-for="row in source.items.filter(item => item.serialRequired)" :key="row.source"><p>{{ row.goodsName }} · 原采购可选序列号：</p><p>{{ row.availableSerials?.length ? row.availableSerials.join('、') : '当前没有可退的原采购序列号' }}</p></div>
      <p>按来源剩余数量估算：未税 {{ Number(source.total).toFixed(4) }} 元，含税 {{ Number(source.actual).toFixed(4) }} 元。实际退货金额须按所选数量重新核算。</p>
    </template>
    <template #footer><el-button @click="$emit('update:modelValue', false)">关闭</el-button><el-button type="primary" :disabled="!source || loading || !!error" @click="source && $emit('continue', source.source, source.sourceVersion)">继续填写退货单</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import type { PurchaseReturnSource } from '@/apis/purchase/returnSource'
defineProps<{ modelValue: boolean; source: PurchaseReturnSource | null; loading: boolean; error: string }>()
defineEmits<{ 'update:modelValue': [value: boolean]; continue: [source: string, version: string] }>()
</script>
