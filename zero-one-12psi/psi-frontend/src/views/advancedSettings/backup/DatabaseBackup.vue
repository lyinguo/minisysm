<template>
  <section class="backup-page">
    <el-card shadow="never">
      <template #header><div class="card-heading"><h2>数据备份</h2><el-tag>数据库 SQL 文件</el-tag></div></template>
      <p class="intro">将当前业务数据库保存为文件，便于在维护、升级前留存数据。</p>
      <el-alert title="备份只读取数据，不修改业务单据、库存或账户余额。" type="info" :closable="false" show-icon />
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="feedback" />
      <el-descriptions v-if="status" :column="1" border class="details">
        <el-descriptions-item label="当前数据库">{{ status.database }}</el-descriptions-item>
        <el-descriptions-item label="业务表数量">{{ status.tables }}</el-descriptions-item>
        <el-descriptions-item label="备份范围">{{ status.scope }}</el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button type="primary" :disabled="!status || checking" :loading="downloading" @click="download">{{ downloading ? '正在生成，请稍候…' : '生成并下载备份' }}</el-button>
        <el-button :loading="checking" :disabled="downloading" @click="check">检查备份环境</el-button>
      </div>
      <p v-if="checking" role="status">正在检查管理员权限及数据库连接…</p>
      <el-alert v-if="lastFile" title="备份文件已生成，下载已发起，请在浏览器下载列表确认保存完成。" type="success" :closable="false" show-icon class="feedback" />
      <p v-if="lastFile" class="file-name">文件：{{ lastFile }}</p>
      <p v-if="checksum" class="checksum">SHA-256：{{ checksum }}</p>
    </el-card>
    <el-card shadow="never">
      <template #header><h3>如何使用</h3></template>
      <ol>
        <li>使用系统管理员账号进入此页，确保 Docker 和 MySQL 容器已启动。</li>
        <li>点击“生成并下载备份”，等待文件生成，确认浏览器已经保存 .sql 文件。</li>
        <li>将文件保存在受控位置。备份包含账号和业务数据，请勿提交到公开代码仓库。</li>
        <li>需要恢复时，先由管理员在独立空数据库中恢复并核对，再安排正式切换。</li>
      </ol>
      <p class="scope-note">本页备份数据库结构和数据，不包含上传附件文件、Redis、Nacos 或服务配置。生成期间请避免数据库结构变更；大型数据库超过处理时限时，需由管理员安排专门备份。</p>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getBackupStatus, downloadDatabaseBackup, type BackupStatus } from '@/apis/systemBackup'
const status = ref<BackupStatus | null>(null)
const checking = ref(false)
const downloading = ref(false)
const error = ref('')
const lastFile = ref('')
const checksum = ref('')
function errorMessage(cause: unknown, fallback: string) {
  if (cause && typeof cause === 'object' && 'message' in cause && typeof cause.message === 'string') return cause.message
  return fallback
}
async function check() {
  if (checking.value || downloading.value) return
  checking.value = true; error.value = ''; status.value = null
  try {
    const result = await getBackupStatus()
    if (result.code !== 10000 || !result.data) throw new Error(result.message || '备份环境检查失败')
    status.value = result.data
  } catch (cause) { error.value = errorMessage(cause, '无法检查备份环境，请确认权限、Docker和MySQL已启动后重试') }
  finally { checking.value = false }
}
async function download() {
  if (!status.value || checking.value || downloading.value) return
  downloading.value = true; error.value = ''; lastFile.value = ''; checksum.value = ''
  try {
    const file = await downloadDatabaseBackup()
    const url = URL.createObjectURL(file.blob)
    try {
      const link = document.createElement('a'); link.href = url; link.download = file.filename
      document.body.appendChild(link); link.click(); link.remove()
      lastFile.value = file.filename; checksum.value = file.sha256
    } finally { setTimeout(() => URL.revokeObjectURL(url), 1000) }
  } catch (cause) { error.value = errorMessage(cause, '备份失败，请重试') }
  finally { downloading.value = false }
}
onMounted(check)
</script>

<style scoped>
.backup-page { display: grid; gap: 20px; max-width: 1000px; margin: 0 auto; padding: 20px; }
.card-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
h2, h3 { margin: 0; }
.intro, li { line-height: 1.8; }
.details, .actions, .feedback { margin-top: 20px; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; }
.actions .el-button { margin-left: 0; }
.scope-note { color: #606266; line-height: 1.8; }
.file-name, .checksum { overflow-wrap: anywhere; }
.checksum { font-family: monospace; color: #606266; }
@media (max-width: 600px) { .backup-page { padding: 8px; } .card-heading { align-items: flex-start; flex-direction: column; } }
</style>
