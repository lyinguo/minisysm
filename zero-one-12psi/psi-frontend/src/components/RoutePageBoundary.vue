<template>
  <el-result
    v-if="failed"
    icon="error"
    title="页面加载失败"
    sub-title="请重试或从左侧菜单切换到其他页面。"
  >
    <template #extra>
      <el-button type="primary" @click="retry">重试</el-button>
    </template>
  </el-result>
  <div v-else :key="attempt" class="route-page-content"><slot /></div>
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'

const failed = ref(false)
const attempt = ref(0)
onErrorCaptured((error, _instance, info) => {
  console.error('[路由页面异常]', info, error)
  failed.value = true
  return false
})
function retry() {
  attempt.value++
  failed.value = false
}
</script>

<style scoped>
.route-page-content {
  height: 100%;
  min-height: 0;
}
</style>
