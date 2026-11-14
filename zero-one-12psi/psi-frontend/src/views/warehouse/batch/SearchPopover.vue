<!--
 * @Description: 仓库管理-批次查询-搜索弹窗
-->
<template>
  <GoodSearchForm v-model="searchForm" :config="searchConfig" @search="handleSearch" />
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import GoodSearchForm from '@/components/goodSearchConpoent/GoodSearchForm.vue'
import type { GoodSearchConfig, SearchFormData } from '@/components/goodSearchConpoent/type'
import type { BatchListRequest } from '@/apis/warehouse/batch/type'

interface PaginationModel {
  pageIndex: number
  pageSize: number
}

const props = defineProps<{
  pagination?: PaginationModel
}>()

const emit = defineEmits<{
  'update:pagination': [value: PaginationModel]
  search: [params: BatchListRequest]
}>()

const searchForm = ref<SearchFormData>({})

const searchConfig = reactive<GoodSearchConfig>({
  showGoods: true,
  showWarehouse: true,
  showNumber: false,
  showSupplier: false,
  showPeople: false,
  showBillDate: false,
  showArrivalDate: false,
  showUser: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  customFields: [
    {
      key: 'goodsNumber',
      label: '请输入商品编号',
      type: 'input'
    },
    {
      key: 'batchNumber',
      label: '请输入批次号码',
      type: 'input'
    },
    {
      key: 'productDate',
      label: '请选择生产日期',
      type: 'date'
    },
    {
      key: 'goodsSpec',
      label: '请输入商品型号',
      type: 'input'
    },
    {
      key: 'goodsCategoryId',
      label: '请选择商品类别',
      type: 'treeSelect',
      checkStrictly: true,
      renderAfterExpand: false,
      clearable: true,
      treeData: [
        {
          value: '0',
          label: '默认类型',
          children: [
            {
              value: '1',
              label: '电子产品',
              children: [
                { value: '1-1', label: '手机' },
                { value: '1-2', label: '电脑' }
              ]
            },
            {
              value: '2',
              label: '服装',
              children: [
                { value: '2-1', label: '男装' },
                { value: '2-2', label: '女装' }
              ]
            }
          ]
        }
      ]
    },
    {
      key: 'goodsBrand',
      label: '请选择商品品牌',
      type: 'select',
      options: []
    },
    {
      key: 'goodsCode',
      label: '请输入商品条码',
      type: 'input'
    },
    {
      key: 'batchState',
      label: '查询类型',
      type: 'select',
      options: [
        { label: '常规批次', value: 0 },
        { label: '预警批次', value: 1 }
      ]
    }
  ]
})

function handleSearch(formData: SearchFormData) {
  const searchParams: BatchListRequest = {
    goodsName: formData.goods || formData.goodsName,
    goodsNumber: formData.goodsNumber,
    batchNumber: formData.batchNumber,
    productDate: formData.productDate,
    goodsSpec: formData.goodsSpec,
    goodsCategoryId: formData.goodsCategoryId,
    goodsBrand: formData.goodsBrand,
    goodsCode: formData.goodsCode,
    warehouseIds: formData.warehouse ? [String(formData.warehouse)] : undefined,
    batchState:
      formData.batchState !== undefined && formData.batchState !== ''
        ? Number(formData.batchState)
        : undefined,
    pageIndex: props.pagination?.pageIndex || 1,
    pageSize: props.pagination?.pageSize || 30
  }

  Object.keys(searchParams).forEach((key) => {
    const paramKey = key as keyof BatchListRequest
    const value = searchParams[paramKey]
    if (
      value === '' ||
      value === null ||
      value === undefined ||
      (Array.isArray(value) && value.length === 0)
    ) {
      delete searchParams[paramKey]
    }
  })

  emit('search', searchParams)
}

defineExpose({
  getFormData: () => searchForm.value,
  resetSearch: () => {
    searchForm.value = {}
  },
  triggerSearch: () => handleSearch(searchForm.value),
  searchForm
})
</script>
