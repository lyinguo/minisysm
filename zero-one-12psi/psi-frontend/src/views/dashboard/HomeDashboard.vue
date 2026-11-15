<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  getStatistics,
  getFunctions,
  getSummary,
  getOverviewPurchase,
  getOverviewPurchaseReturn,
  getOverviewSale,
  getOverviewSaleReturn,
  getOverviewReceipt,
  getOverviewPayment,
  getOverviewStock,
  getAssets,
  getFunds
} from '@/apis/dashboard/dashboard'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import GettingStarted from '@/components/workspace/GettingStarted.vue'
import { useUserStore } from '@/stores/user'
import { navigationEntries } from '@/utils/workspaceNavigation'

type FundItem = { name: string; value: number }

const router = useRouter()
const userStore = useUserStore()
const destinations = computed(() => navigationEntries(userStore.menus || [], path => router.resolve(path).matched.length > 0 && router.resolve(path).name !== 'NotFound'))
const availablePath = (path: string) => destinations.value.some(entry => entry.path === path)
const go = (path: string) => {
  if (availablePath(path)) void router.push(path)
  else ElMessage.info('当前入口不可用，请通过顶部搜索或左侧菜单选择业务页面')
}
const dashboardLoading = ref(true)
const failedSections = ref(0)

/* ========================= 顶部四项统计 ========================= */
type KpiItem = {
  key: string
  label: string
  value: number
  rate: number
  unit?: string
  to: string
}
const kpis = ref<KpiItem[]>([])

/* ========================= 常用功能 + 汇总信息 ========================= */
const shortcuts = ref<{ label: string; to: string }[]>([])
const summary = ref<{ label: string; value: number; to: string }[]>([])

/* ========================= 数据概览 ========================= */
const overviewRef = ref<HTMLDivElement | null>(null)
let overviewChart: echarts.ECharts | null = null

const chartTitles = ['采购单', '采购退货单', '销售单', '销售退货单', '收款单', '付款单', '库存数据']
const dots = Array.from({ length: 7 }, (_, i) => i)
const activeDot = ref(0)
const activeTitle = computed(() => chartTitles[activeDot.value])
const overviewData = ref<{ date: string; value: number }[]>([])
const stockData = ref<{ name: string; value: number }[]>([])

/* ========================= 资产数据 & 资金数据 ========================= */
const assets = ref<{ label: string; value: string; to: string }[]>([])
const totalAsset = computed(() =>
  assets.value.reduce((sum, item) => {
    const num = parseFloat(item.value.replace(/[^\d.-]/g, ''))
    return sum + (isNaN(num) ? 0 : num)
  }, 0)
)

const fundsRef = ref<HTMLDivElement | null>(null)
let fundsChart: echarts.ECharts | null = null
const fundsData = ref<FundItem[]>([])
const COLOR_NEG = '#8b6f47'
const COLOR_POS = '#52c41a'

/* ========================= 数据获取 ========================= */

// 顶部四项
async function fetchStatistics() {
  const { data } = await getStatistics()
  if (!data) return
  kpis.value = [
    {
      key: 'sales',
      label: '日销售额',
      value: data.dailySales.amount,
      rate: data.dailySales.rate,
      unit: '元',
      to: '/report/sales/summary'
    },
    {
      key: 'gross',
      label: '日销售毛利',
      value: data.dailyGross.amount,
      rate: data.dailyGross.rate,
      unit: '元',
      to: '/report/sales/profit'
    },
    {
      key: 'count',
      label: '日销售笔数',
      value: data.dailyCount.amount,
      rate: data.dailyCount.rate,
      unit: '笔',
      to: '/report/sales/detail'
    },
    {
      key: 'income',
      label: '日资金收入',
      value: data.dailyIncome.amount,
      rate: data.dailyIncome.rate,
      unit: '元',
      to: '/receipt-order-report'
    }
  ]
}

// 常用功能
async function fetchShortcuts() {
  const { data } = await getFunctions()
  if (!data) return
  shortcuts.value = Array.isArray(data) ? data.filter(item => availablePath(item.to)) : []
}

// 汇总信息
async function fetchSummary() {
  const { data } = await getSummary()
  if (!data) return
  summary.value = data
}

// 数据概览
const today = dayjs().format('YYYY-MM-DD')
const thirtyDaysAgo = dayjs().subtract(29, 'day').format('YYYY-MM-DD')
const defaultRange = { startDate: thirtyDaysAgo, endDate: today } //采购单
const purchaseReturnParams = {
  type: '采购退货单', // 采购退货单
  startDate: thirtyDaysAgo, // 复用已有的日期
  endDate: today
}
const saleParams = {
  type: '销售单', //销售单
  startDate: thirtyDaysAgo,
  endDate: today
}
const saleReturnParams = { type: '销售退货单' } //销售退货单
const receiptParams = { type: '收款单' } // 收款单
const defaultPaymentParams = { type: '付款单', from: thirtyDaysAgo, to: today }

async function fetchOverviewData(i = activeDot.value) {
  const overviewFetchers = [
    () => getOverviewPurchase(defaultRange),
    () => getOverviewPurchaseReturn(purchaseReturnParams),
    () => getOverviewSale(saleParams),
    () => getOverviewSaleReturn(saleReturnParams),
    () => getOverviewReceipt(receiptParams),
    () => getOverviewPayment(defaultPaymentParams),
    getOverviewStock
    // () => getOverviewStock(defaultRange),
  ]

  const fetcher = overviewFetchers[i]
  const { data } = await fetcher()
  if (!data) {
    if (i < 6) overviewData.value = []
    else stockData.value = []
    return
  }
  if (i < 6) {
    // 折线图：date-value 对应
    overviewData.value = data.list as { date: string; value: number }[]
  } else {
    // 饼图：name-value 对应
    stockData.value = data.list as { name: string; value: number }[]
  }

  drawOverview()
}

// 资产数据
async function fetchAssets() {
  const { data } = await getAssets()
  if (!data) return
  assets.value = data.list
}

// 资金数据
async function fetchFundsData() {
  const { data } = await getFunds()
  if (!data) return
  fundsData.value = (data.list || []).slice(0, 5)
  drawFunds()
}

/* ========================= 图表渲染 ========================= */
function drawOverview() {
  if (!overviewRef.value) return
  if (!overviewChart) overviewChart = echarts.init(overviewRef.value)

  if (activeDot.value < 6) {
    const option: echarts.EChartsOption = {
      tooltip: { trigger: 'axis' },
      grid: { top: 30, left: 40, right: 20, bottom: 30 },
      xAxis: { type: 'category', boundaryGap: false, data: overviewData.value.map((d) => d.date) },
      yAxis: { type: 'value' },
      series: [
        {
          name: activeTitle.value,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          data: overviewData.value.map((d) => d.value),
          areaStyle: {}
        }
      ]
    }
    overviewChart.setOption(option)
  } else {
    const option: echarts.EChartsOption = {
      tooltip: { trigger: 'item' },
      legend: { top: '5%', left: 'center' },
      series: [
        {
          name: '库存分布',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          label: { show: true, formatter: '{b}: {c}' },
          data: stockData.value
        }
      ]
    }
    overviewChart.setOption(option)
  }
}

function hoverDot(i: number) {
  activeDot.value = i
  fetchOverviewData(i)
}

function drawFunds() {
  if (!fundsRef.value) return
  if (!fundsChart) fundsChart = echarts.init(fundsRef.value)

  const categories = fundsData.value.map((d) => d.name)
  const seriesData = fundsData.value.map((d) => ({
    value: d.value,
    itemStyle: { color: d.value >= 0 ? COLOR_POS : COLOR_NEG }
  }))

  // 一个简单的换行函数：每 6 个字符换一行，你可以根据实际长度调整
  const wrapLabel = (value: string) => {
    const maxLen = 7 // 每行最多几个字符
    if (!value || value.length <= maxLen) return value
    const lines: string[] = []
    for (let i = 0; i < value.length; i += maxLen) {
      lines.push(value.slice(i, i + maxLen))
    }
    return lines.join('\n') // 用换行符分行
  }

  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}：{c}' },
    grid: { top: 20, left: 60, right: 20, bottom: 80 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#666', fontSize: 13, formatter: (value: string) => wrapLabel(value) },

      axisLine: { lineStyle: { color: '#ccc' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#e9e9e9' } }
    },
    series: [
      {
        type: 'bar',
        data: seriesData,
        barWidth: 100,
        label: { show: true, position: 'top', color: '#333', fontWeight: 600, formatter: '{c}' },
        itemStyle: { borderRadius: [4, 4, 0, 0] }
      }
    ]
  }

  fundsChart.setOption(option)
}

/* ========================= 生命周期 ========================= */
const resizeCharts = () => { overviewChart?.resize(); fundsChart?.resize() }
onMounted(async () => {
  window.addEventListener('resize', resizeCharts)
  const results = await Promise.allSettled([
    fetchStatistics(),
    fetchShortcuts(),
    fetchSummary(),
    fetchAssets(),
    fetchFundsData(),
    fetchOverviewData(0)
  ])
  failedSections.value = results.filter(result => result.status === 'rejected').length
  dashboardLoading.value = false
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  overviewChart?.dispose()
  fundsChart?.dispose()
})
</script>

<template>
  <div class="home">
    <GettingStarted />
    <el-alert v-if="failedSections" title="部分统计暂未加载成功，可继续使用业务入口，稍后刷新页面重试。" type="warning" :closable="false" show-icon />
    <div class="dashboard-section-heading"><h2>经营概览</h2><span>统计数据以已录入的业务为准</span></div>
    <!-- 顶部统计 -->
    <div v-if="kpis.length || dashboardLoading" v-loading="dashboardLoading" class="top-row">
      <button v-for="item in kpis" :key="item.key" type="button" class="kpi-card hoverable" :disabled="!availablePath(item.to)" :title="availablePath(item.to) ? '查看相关报表' : '当前账号没有相关报表入口'" @click="go(item.to)">
        <div class="kpi-header">
          <span>{{ item.label }}</span>
        </div>
        <div class="kpi-body">
          <div class="amount">{{ item.value }}{{ item.unit }}</div>
          <div class="rate" :style="{ color: item.rate >= 0 ? '#4caf50' : '#f44336' }">
            {{ item.rate }}%
          </div>
        </div>
      </button>
    </div>

    <!-- 常用功能 & 汇总信息 -->
    <div class="section">
      <div class="panel">
        <div class="panel-title">常用功能</div>
        <div class="panel-content shortcuts">
          <div v-for="s in shortcuts" :key="s.label" class="shortcut hoverable" @click="go(s.to)">
            <span>{{ s.label }}</span>
          </div>
          <p v-if="!shortcuts.length" class="dashboard-empty">可从上方业务入口或顶部功能搜索开始。</p>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">汇总信息</div>
        <div class="panel-content summary">
          <div v-for="s in summary" :key="s.label" class="summary-item hoverable" @click="go(s.to)">
            <div class="name">{{ s.label }}</div>
            <div class="num">{{ s.value }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据概览 -->
    <div class="panel">
      <div class="panel-title flex-between">
        <span>{{ activeTitle }}</span>
        <div class="dots">
          <span
            v-for="i in dots"
            :key="i"
            class="dot"
            :class="{ active: activeDot === i }"
            role="button" tabindex="0" :aria-label="'查看' + chartTitles[i]" :title="chartTitles[i]" :aria-pressed="activeDot === i"
            @click="hoverDot(i)" @keydown.enter="hoverDot(i)" @keydown.space.prevent="hoverDot(i)"
          >{{ chartTitles[i] }}</span>
        </div>
      </div>
      <div class="chart-panel"><div ref="overviewRef" class="chart"></div><el-empty v-if="!dashboardLoading && !(activeDot < 6 ? overviewData.length : stockData.length)" description="暂无可用统计数据" :image-size="64" /></div>
    </div>

    <!-- 底部资产 & 资金 -->
    <div class="bottom">
      <div class="panel">
        <div class="panel-title">资产数据</div>
        <div v-if="assets.length" class="total">总资产：{{ totalAsset.toFixed(2) }} 元</div>
        <el-empty v-else-if="!dashboardLoading" description="暂无可用资产数据" :image-size="64" />
        <div class="asset-list">
          <div v-for="a in assets" :key="a.label" class="asset-item hoverable" @click="go(a.to)">
            <div class="left">{{ a.label }}</div>
            <div class="right">{{ a.value }}</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">资金数据</div>
        <div class="chart-panel"><div ref="fundsRef" class="funds-chart"></div><el-empty v-if="!dashboardLoading && !fundsData.length" description="暂无可用资金数据" :image-size="64" /></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding: 16px;
  background: #f6f8fa;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.top-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.kpi-header {
  font-weight: 600;
  color: #666;
}
.kpi-body {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.amount {
  font-size: 20px;
  font-weight: 700;
}
.rate {
  font-weight: 600;
}

.section {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
}
.panel {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
}
.panel-title {
  font-weight: 600;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}
.shortcuts {
  display: flex;
  justify-content: space-around;
  padding-top: 10px;
}
.shortcut {
  background: #fafafa;
  padding: 14px 0;
  width: 22%;
  text-align: center;
  border-radius: 8px;
  border: 1px solid #f1f1f1;
}
.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding-top: 10px;
}
.summary-item {
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f1f1f1;
  padding: 10px;
}
.name {
  color: #666;
}
.num {
  font-size: 20px;
  font-weight: 700;
  margin-top: 4px;
}

.chart {
  height: 320px;
}

.dots {
  display: flex;
  gap: 8px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}
.dot.active {
  background: #333;
}

.bottom {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px;
}
.total {
  font-weight: 600;
  padding: 8px 0;
}
.asset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.asset-item {
  background: #fafafa;
  border: 1px solid #f1f1f1;
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
}
.funds-chart {
  height: 260px;
  width: 100%;
}
.hoverable {
  cursor: pointer;
  transition: 0.1s;
}
.hoverable:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
}
</style>

<style scoped>
.home{padding:0;background:transparent;gap:20px}.dashboard-section-heading{display:flex;align-items:center;gap:12px;margin:8px 0 -6px}.dashboard-section-heading h2{font-size:17px;font-weight:600;color:#26344a}.dashboard-section-heading span{font-size:12px;color:#8490a3}.kpi-card{border:1px solid #e5eaf1;box-shadow:none;min-height:115px;text-align:left;font:inherit;gap:16px;padding:20px}.kpi-card:disabled{cursor:default;opacity:.8}.kpi-card:disabled:hover{transform:none;box-shadow:none}.amount{font-size:27px;font-variant-numeric:tabular-nums;color:#26344a}.rate{font-size:12px}.panel{border:1px solid #e5eaf1;padding:20px}.panel-title{padding-bottom:14px;color:#34455f;font-size:14px;gap:16px;flex-wrap:wrap}.dots{flex-wrap:wrap;gap:5px}.dot{width:auto;height:auto;border-radius:6px;padding:5px 9px;font-size:11px;line-height:1.4;background:#f3f6fb;color:#7a899f;cursor:pointer}.dot.active{background:#ecf2ff;color:#3565dc}.dashboard-empty{font-size:13px;color:#8a95a6;padding:14px 0}.shortcut{border-radius:8px;background:#f5f8ff;color:#4c6ba8}.asset-item{background:#f8faff;border:0}.total{color:#3565dc;font-size:18px;padding:20px 0}
@media(max-width:1050px){.top-row{grid-template-columns:repeat(2,minmax(0,1fr))}.section,.bottom{grid-template-columns:1fr}.panel{padding:16px}}@media(max-width:560px){.top-row{grid-template-columns:1fr}.dashboard-section-heading{align-items:flex-start;flex-direction:column;gap:4px}.amount{font-size:24px}.chart{height:260px}}
</style>

<style scoped>.chart-panel{position:relative}.chart-panel>.el-empty{position:absolute;inset:0;pointer-events:none}</style>
