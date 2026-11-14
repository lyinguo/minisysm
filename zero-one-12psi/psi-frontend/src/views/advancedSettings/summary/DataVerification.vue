<template>
  <section class="verification-page">
    <h2>数据核准</h2>
    <el-alert
      title="当前可通过下方报表核对数据；全量成本重算尚未接入。"
      description="原系统的数据核准会按计价规则重新计算单据收发成本。本页提供现有核对入口，查看这些报表不会修改库存或财务数据。"
      type="info"
      :closable="false"
      show-icon
    />
    <div class="verification-links">
      <el-card v-for="item in checks" :key="item.path" shadow="hover">
        <template #header>{{ item.title }}</template>
        <p>{{ item.description }}</p>
        <el-button type="primary" @click="router.push(item.path)">{{ item.action }}</el-button>
      </el-card>
    </div>
    <el-card>
      <template #header>核对顺序</template>
      <ol>
        <li>查看商品库存余额，确认商品及仓库的当前数量。</li>
        <li>查看商品收发明细，核对入库、出库和调拨记录。</li>
        <li>查看收发汇总及操作日志，定位差异对应的单据和操作。</li>
        <li>发现差异时先核实原单据，不要直接将报表汇总数作为库存修改值。</li>
      </ol>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const checks = [
  {
    title: '商品库存余额',
    description: '按商品、仓库查看当前库存数量和成本。',
    path: '/report/warehouse/inventory-summary',
    action: '查看库存余额'
  },
  {
    title: '商品收发明细',
    description: '追查单据对应的出入库数量及结存记录。',
    path: '/report/warehouse/receipt-detail',
    action: '查看收发明细'
  },
  {
    title: '商品收发汇总',
    description: '核对采购、销售、调拨及其他出入库的汇总变化。',
    path: '/report/warehouse/receipt-summary',
    action: '查看收发汇总'
  },
  {
    title: '操作日志',
    description: '辅助核对单据修改、审核及反审核的操作记录。',
    path: '/operation-log',
    action: '查看操作日志'
  }
]
</script>

<style scoped>
.verification-page {
  padding: 20px;
  height: 100%;
  overflow: auto;
  box-sizing: border-box;
}
h2 {
  margin: 0 0 16px;
}
.verification-links {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin: 20px 0;
}
p {
  min-height: 42px;
  color: #606266;
}
li {
  margin: 10px 0;
  line-height: 1.6;
}
</style>
