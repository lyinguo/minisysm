<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ArrowRight, Box, ShoppingCart, Sell, Wallet } from '@element-plus/icons-vue'
import { navigationEntries } from '@/utils/workspaceNavigation'
const router = useRouter()
const store = useUserStore()
const allowed = computed(() => new Set(navigationEntries(store.menus || [], path => router.resolve(path).matched.length > 0 && router.resolve(path).name !== 'NotFound').map(entry => entry.path)))
const workflows = [
  { title: '先准备基础资料', icon: Box, detail: '先有商品、往来单位和仓库，开单时才有内容可选。', links: [{ label: '商品', path: '/product-manage' }, { label: '客户', path: '/customer-manage' }, { label: '供应商', path: '/supplier-manage' }, { label: '仓库', path: '/warehouse-manage' }] },
  { title: '我要采购进货', icon: ShoppingCart, detail: '选供应商和商品，录入采购业务，再核对入库和付款。', links: [{ label: '采购订单', path: '/purchase-booking' }, { label: '采购单', path: '/purchase-order' }, { label: '采购汇总', path: '/report/purchase/summary' }] },
  { title: '我要销售出货', icon: Sell, detail: '选客户和商品，录入销售业务，再核对出库和收款。', links: [{ label: '销售订单', path: '/sales-booking' }, { label: '销售单', path: '/sales-order' }, { label: '销售汇总', path: '/report/sales/summary' }] },
  { title: '核对库存与资金', icon: Wallet, detail: '库存按仓库和商品查询，往来收付款在资金业务中处理。', links: [{ label: '查库存', path: '/inventory-query' }, { label: '收款', path: '/receipt-order' }, { label: '付款', path: '/payment-order' }, { label: '资金账户', path: '/fund-account' }] }
]
const cards = computed(() => workflows.map(card => ({ ...card, links: card.links.filter(link => allowed.value.has(link.path)) })).filter(card => card.links.length))
</script>
<template>
  <section class="getting-started" aria-label="业务使用入口">
    <div class="getting-started__intro"><span class="intro-kicker">业务工作台</span><h2>今天，从哪项业务开始？</h2><p>第一次使用，建议先准备基础资料。每个页面的“如何使用”里都有操作说明。</p></div>
    <div class="workflow-grid">
      <article v-for="(card, index) in cards" :key="card.title" class="workflow-card">
        <div class="workflow-card__top"><span class="workflow-icon"><el-icon><component :is="card.icon" /></el-icon></span><span class="workflow-number">0{{ index + 1 }}</span></div>
        <h3>{{ card.title }}</h3><p>{{ card.detail }}</p>
        <div class="workflow-links"><button v-for="link in card.links" :key="link.path" type="button" @click="router.push(link.path)">{{ link.label }}<el-icon><ArrowRight /></el-icon></button></div>
      </article>
    </div>
    <p v-if="!cards.length" class="no-workflow">当前账号暂无业务入口，请联系管理员分配菜单权限。</p>
  </section>
</template>
<style scoped>
.getting-started{margin-bottom:6px}.getting-started__intro{padding:8px 0 22px}.intro-kicker{font-size:11px;letter-spacing:2px;font-weight:600;color:#3565dc}h2{font-size:25px;font-weight:650;line-height:1.5;color:#1d2b43;margin:5px 0}p{font-size:13px;color:#7a899f;line-height:1.8;margin:0}.workflow-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.workflow-card{background:#fff;border:1px solid #e5eaf1;border-radius:12px;padding:21px 20px;display:flex;flex-direction:column;transition:border-color .2s,box-shadow .2s}.workflow-card:hover{border-color:#b7cafa;box-shadow:0 5px 18px #29427208}.workflow-card__top{display:flex;justify-content:space-between;align-items:center}.workflow-icon{display:flex;align-items:center;justify-content:center;background:#edf3ff;color:#3565dc;border-radius:11px;width:40px;height:40px;font-size:21px}.workflow-card:nth-child(2) .workflow-icon{background:#ecf9f5;color:#219579}.workflow-card:nth-child(3) .workflow-icon{background:#f3efff;color:#8663c6}.workflow-card:nth-child(4) .workflow-icon{background:#fff6e9;color:#bd852a}.workflow-number{font-size:25px;font-weight:650;color:#e5ebf5}h3{font-size:15px;font-weight:600;color:#26344a;margin:17px 0 7px}.workflow-card p{font-size:12px;flex:1;min-height:44px}.workflow-links{display:flex;flex-wrap:wrap;gap:9px 14px;border-top:1px solid #edf1f7;padding-top:14px;margin-top:18px}.workflow-links button{border:0;background:none;padding:0;font-size:12px;color:#4e6faa;cursor:pointer;display:flex;align-items:center;gap:2px}.workflow-links button:hover{color:#244fb8}.no-workflow{padding:20px;background:#fff;border-radius:12px}
@media(max-width:1200px){.workflow-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.workflow-grid{grid-template-columns:1fr}h2{font-size:22px}.workflow-card{padding:16px}.workflow-card p{min-height:0}}
</style>
