<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleDialogUpdate"
    title="发票开具"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="100px" ref="formRef" :rules="rules">
      <el-form-item label="合计金额" prop="totalAmount">
        <el-input v-model="form.totalAmount" disabled />
      </el-form-item>
      <el-form-item label="开票时间" prop="invoiceDate">
        <el-date-picker
          v-model="form.invoiceDate"
          type="date"
          placeholder="选择开票时间"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="发票号码" prop="invoiceNumber">
        <el-input v-model="form.invoiceNumber" placeholder="请输入发票号码" />
      </el-form-item>
      <el-form-item label="发票抬头" prop="invoiceTitle">
        <el-input v-model="form.invoiceTitle" placeholder="请输入发票抬头" />
      </el-form-item>
      <el-form-item label="发票附件" prop="attachment">
        <el-upload
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :file-list="fileList"
        >
          <el-button type="primary">点击上传</el-button>
        </el-upload>
      </el-form-item>
      <el-form-item label="备注信息" prop="remark">
        <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注信息" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm" :loading="loading">开票</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { TradeInvoiceAPI } from '@/apis/finance/otherDocuments'

interface InvoiceForm {
  totalAmount: number
  invoiceDate: string
  invoiceNumber: string
  invoiceTitle: string
  attachment?: File
  remark: string
}

interface Props {
  visible: boolean
  selectedRecords: any[]
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'invoice-success'])

const formRef = ref()
const loading = ref(false)
const fileList = ref<UploadFile[]>([])

const form = reactive<InvoiceForm>({
  totalAmount: 0,
  invoiceDate: '',
  invoiceNumber: '',
  invoiceTitle: '',
  remark: ''
})

const rules = {
  invoiceDate: [{ required: true, message: '请选择开票时间', trigger: 'change' }],
  invoiceNumber: [{ required: true, message: '请输入发票号码', trigger: 'blur' }],
  invoiceTitle: [{ required: true, message: '请输入发票抬头', trigger: 'blur' }]
}

const handleDialogUpdate = (value: boolean) => {
  emit('update:visible', value)
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      form.totalAmount = props.selectedRecords.reduce((sum, record) => {
        return sum + (Number(record.invoiceAmount) || 0)
      }, 0)
      form.invoiceDate = new Date().toISOString().slice(0, 10)
      form.invoiceNumber = ''
      form.invoiceTitle = props.selectedRecords[0]?.contactUnit || ''
      form.remark = ''
      fileList.value = []
    }
  }
)

const handleFileChange = (file: UploadFile) => {
  form.attachment = file.raw
}

const handleClose = () => {
  emit('update:visible', false)
}

const handleConfirm = async () => {
  if (!formRef.value) return

  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    const infos = props.selectedRecords.map((record) => ({
      type: record.typeCode,
      id: String(record.id),
      amount: Math.abs(Number(record.invoiceAmount) || 0)
    }))

    if (infos.some((item) => !item.type || !item.id || !item.amount)) {
      ElMessage.error('所选单据信息不完整，无法开票')
      return
    }

    loading.value = true
    const body = {
      infos,
      time: `${form.invoiceDate} 00:00:00`,
      number: form.invoiceNumber,
      title: form.invoiceTitle,
      file: form.attachment ? form.attachment.name : '',
      data: form.remark
    }

    const res = await TradeInvoiceAPI.add(body)
    if (res?.code !== 10000) {
      throw new Error(res?.message || '开票失败')
    }

    emit('invoice-success')
    handleClose()
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '开票失败')
  } finally {
    loading.value = false
  }
}
</script>
