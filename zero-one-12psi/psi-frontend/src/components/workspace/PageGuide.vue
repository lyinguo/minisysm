<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { QuestionFilled, ArrowRight } from '@element-plus/icons-vue'
import { navigationEntries, usageGuide } from '@/utils/workspaceNavigation'
import { useUserStore } from '@/stores/user'
const route = useRoute()
const router = useRouter()
const user = useUserStore()
const relatedPage = computed(() => {
  const match = route.path.match(/^\/(purchase|sales)-(booking|order|return)(-report)?$/)
  if (!match) return undefined
  const path = match[3] ? route.path.replace(/-report$/, '') : route.path + '-report'
  const target = navigationEntries(user.menus, value => router.resolve(value).matched.length > 0).find(entry => entry.path === path)
  if (!target) return undefined
  return { path, label: match[3] ? '前往开单' : '查询已保存单据' }
})
const open = ref(false)
const guide = computed(() => usageGuide(route.path))
const title = computed(() => route.path === '/dashboard' ? '工作台' : String(route.meta.label || guide.value.group))
watch(() => route.path, () => { open.value = false })
</script>
<template>
  <section class="page-guide" aria-label="当前页面说明">
    <div class="page-guide__heading">
      <div class="page-guide__copy">
        <div class="page-guide__breadcrumb">{{ guide.group }} <template v-if="title !== guide.group"><el-icon><ArrowRight /></el-icon> {{ title }}</template></div>
        <h1>{{ title }}</h1>
        <p>{{ guide.summary }}</p>
      </div>
      <div class="page-guide__actions">
        <el-button v-if="relatedPage" type="primary" plain @click="router.push(relatedPage.path)">{{ relatedPage.label }}</el-button>
        <el-button :icon="QuestionFilled" :aria-expanded="open" aria-controls="page-operation-guide" @click="open = !open">{{ open ? '收起指引' : '如何使用' }}</el-button>
      </div>
    </div>
    <div v-if="open" id="page-operation-guide" class="page-guide__instructions">
      <ol><li v-for="step in guide.steps" :key="step">{{ step }}</li></ol>
      <p v-if="guide.note" class="page-guide__note">{{ guide.note }}</p>
    </div>
  </section>
</template>
<style scoped>
.page-guide{flex:none;padding:22px 26px 18px;background:#fff;border-bottom:1px solid var(--psi-border,#e5eaf1)}
.page-guide__heading{display:flex;align-items:center;justify-content:space-between;gap:24px}.page-guide__copy{min-width:0}
.page-guide__actions{display:flex;gap:8px;flex-wrap:wrap;flex:none}.page-guide__actions .el-button+.el-button{margin-left:0}
.page-guide__breadcrumb{display:flex;align-items:center;gap:8px;font-size:12px;color:#8490a3;margin-bottom:7px}
h1{font-size:23px;line-height:1.35;font-weight:650;color:#1d2b43;margin:0 0 6px}p{margin:0;color:#68788f;font-size:13px;line-height:1.7}
.page-guide__instructions{background:#f3f7ff;border:1px solid #dee8ff;border-radius:10px;margin-top:16px;padding:14px 18px}
ol{padding-left:20px;display:grid;gap:7px;color:#3c506e;font-size:13px}.page-guide__note{margin-top:12px;color:#716034}
@media(max-width:720px){.page-guide__heading{flex-wrap:wrap}.page-guide__actions{width:100%}.page-guide__actions .el-button{padding:8px;font-size:12px}}
@media(max-width:720px){.page-guide{padding:14px 16px}.page-guide__heading{align-items:flex-start;gap:12px}h1{font-size:20px}.page-guide__breadcrumb{display:none}.page-guide__heading>.el-button{padding:8px;font-size:12px}p{font-size:12px}}
</style>
