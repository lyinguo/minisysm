import type { RouteRecordRaw } from 'vue-router'

/*
 * @Description: 仓库管理的路由
 */
const routes: RouteRecordRaw[] = [
  // 基础查询功能
  {
    path: 'inventory-query',
    name: 'WarehouseInventoryQuery',
    meta: {
      label: '库存查询',
      icon: 'mdi:package-variant'
    },
    component: () => import('@/views/warehouse/inventory/Index.vue')
  },
  {
    path: 'batch-query',
    name: 'WarehouseBatchQuery',
    meta: {
      label: '批次查询',
      icon: 'mdi:package-variant-closed'
    },
    component: () => import('@/views/warehouse/batch/Index.vue')
  },
  {
    path: 'serial-query',
    name: 'WarehouseSerialQuery',
    meta: {
      label: '序列查询',
      icon: 'mdi:barcode'
    },
    component: () => import('@/views/warehouse/serial/Index.vue')
  },
  // 兼容后端菜单历史路径 /room/serial
  {
    path: 'room/serial',
    redirect: '/serial-query'
  },
  {
    path: 'inventory-check',
    name: 'WarehouseInventoryCheck',
    meta: {
      label: '库存盘点',
      icon: 'mdi:clipboard-list'
    },
    component: () => import('@/views/warehouse/check/Index.vue')
  },

  // 其他出入库和调拨
  {
    path: 'other-inbound',
    name: 'WarehouseOtherInbound',
    meta: {
      label: '其他入库单',
      icon: 'mdi:package-down'
    },
    component: () => import('@/views/warehouse/inbound/OtherInbound.vue')
  },
  {
    path: 'other-outbound',
    name: 'WarehouseOtherOutbound',
    meta: {
      label: '其他出库单',
      icon: 'mdi:package-up'
    },
    component: () => import('@/views/warehouse/outbound/OtherOutbound.vue')
  },
  {
    path: 'transfer-order',
    name: 'WarehouseTransferOrder',
    meta: {
      label: '调拨单',
      icon: 'mdi:truck-delivery'
    },
    component: () => import('@/views/warehouse/transfer/TransferOrder.vue')
  },

  // 报表
  {
    path: 'transfer-order-report',
    name: 'WarehouseTransferOrderReport',
    meta: {
      label: '调拨单报表',
      icon: 'mdi:file-chart'
    },
    component: () => import('@/views/warehouse/transfer/TransferOrderReport.vue')
  },
  {
    path: 'other-inbound-report',
    name: 'WarehouseOtherInboundReport',
    meta: {
      label: '其他入库单报表',
      icon: 'mdi:file-chart'
    },
    component: () => import('@/views/warehouse/inbound/OtherInboundReport.vue')
  },
  {
    path: 'other-outbound-report',
    name: 'WarehouseOtherOutboundReport',
    meta: {
      label: '其他出库单报表',
      icon: 'mdi:file-chart'
    },
    component: () => import('@/views/warehouse/outbound/OtherOutboundReport.vue')
  },

  // 单据管理（跳转至已实现的功能页，避免占位页）
  {
    path: 'inbound-order',
    redirect: '/other-inbound'
  },
  {
    path: 'outbound-order',
    redirect: '/other-outbound'
  },
  {
    path: 'document-transfer-order',
    redirect: '/transfer-order'
  },
  {
    path: 'inventory-check-order',
    redirect: '/inventory-check'
  },
  {
    path: 'assemble-disassemble',
    redirect: '/inventory-check'
  }
]

export default routes
