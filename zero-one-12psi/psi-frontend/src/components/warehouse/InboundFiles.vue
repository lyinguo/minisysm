<template>
  <el-button :disabled="disabled" @click="visible = true">批量导入入库单</el-button>
  <el-dialog
    v-model="visible"
    title="从 Excel 导入入库草稿"
    width="850px"
    :close-on-click-modal="false"
  >
    <el-alert
      title="用于非采购入库。先下载模板填写商品和仓库编号，再预览核对；确认只保存草稿，审核后才增加库存。"
      type="info"
      :closable="false"
    />
    <p><el-button :disabled="busy" @click="template">下载模板（含填写说明）</el-button></p>
    <label
      >选择填写后的 Excel 文件
      <input type="file" accept=".xlsx,.xls" :disabled="busy" @change="selected"
    /></label>
    <p v-if="file">
      已选：{{ file.name }} <el-button :loading="busy" @click="preview">上传并预览</el-button>
    </p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template v-if="plan">
      <p>
        将生成 {{ plan.documentCount }} 张草稿、{{ plan.lineCount }} 行商品，成本合计
        {{ Number(plan.total).toFixed(4) }} 元；所属组织和制单人使用当前登录账号。
      </p>
      <el-table :data="plan.references" border max-height="300">
        <el-table-column prop="number" label="入库单号" min-width="170" />
        <el-table-column label="实际商品" min-width="160"
          ><template #default="{ row }"
            >{{ row.goods.name }}（{{ row.goods.number }}）</template
          ></el-table-column
        >
        <el-table-column label="实际仓库" min-width="170"
          ><template #default="{ row }"
            >{{ row.warehouse.name }}（{{ row.warehouse.number }}）</template
          ></el-table-column
        >
        <el-table-column prop="unit" label="基本单位" width="90" />
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="price" label="单位成本" width="110" />
      </el-table>
      <p>确认前请核对单号、商品和仓库。任何一行失败，整批不保存。</p>
      <el-button type="primary" :loading="busy" @click="confirm"
        >确认生成 {{ plan.documentCount }} 张草稿</el-button
      >
    </template>
    <template v-if="saved.length">
      <el-alert
        title="入库草稿已真实保存，尚未增加库存。点击单据打开并继续核对、审核。"
        type="success"
        :closable="false"
      />
      <p v-for="document in saved" :key="document.id">
        <el-button link type="primary" @click="showDocument(document.id)"
          >打开 {{ document.number }}</el-button
        >
      </p>
    </template>
  </el-dialog>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import { downloadExportBlob } from '@/utils/reportMappers'
defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ saved: []; open: [id: string] }>()
const http = useHttp(),
  visible = ref(false),
  busy = ref(false),
  error = ref(''),
  file = ref<File>(),
  plan = ref<any>(),
  saved = ref<{ id: string; number: string }[]>([])
function selected(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0]
  plan.value = undefined
  saved.value = []
  error.value = ''
}
function unwrap(result: any) {
  if (result?.code !== 10000 || !result.data) throw Error(extractErrorMessage(result))
  return result.data
}
async function template() {
  busy.value = true
  error.value = ''
  try {
    downloadExportBlob(
      await http.getFile('/otherin/import/template', {}, { responseType: 'blob' }),
      '其他入库模板.xlsx'
    )
  } catch (e) {
    error.value = extractErrorMessage(e)
  } finally {
    busy.value = false
  }
}
async function preview() {
  if (!file.value || busy.value) return
  busy.value = true
  plan.value = undefined
  saved.value = []
  error.value = ''
  try {
    const data = unwrap(await http.postWithFile('/otherin/import', { file: file.value }))
    if (
      !/^[0-9a-f]{64}$/.test(data.version) ||
      !Array.isArray(data.references) ||
      !Array.isArray(data.documents) ||
      data.documentCount !== data.documents.length ||
      data.lineCount !== data.references.length
    )
      throw Error('预览结果不完整，请重新选择文件')
    plan.value = data
  } catch (e) {
    error.value = extractErrorMessage(e)
  } finally {
    busy.value = false
  }
}
async function confirm() {
  if (!plan.value || !file.value || busy.value) return
  try {
    await ElMessageBox.confirm(
      `确认保存 ${plan.value.documentCount} 张入库草稿？不会自动审核或增加库存。`,
      '确认导入',
      { type: 'warning' }
    )
    busy.value = true
    error.value = ''
    const result = unwrap(
      await http.postWithFile('/otherin/import', { file: file.value, version: plan.value.version })
    )
    if (!Array.isArray(result.ids) || result.ids.length !== plan.value.documentCount)
      throw Error('未收到完整单据ID，请先查询结果，避免重复导入')
    saved.value = result.ids.map((id: string, index: number) => ({
      id,
      number: plan.value.documents[index].number
    }))
    plan.value = undefined
    emit('saved')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      error.value = extractErrorMessage(e)
      plan.value = undefined
    }
  } finally {
    busy.value = false
  }
}
function showDocument(id: string) {
  visible.value = false
  emit('open', id)
}
</script>
