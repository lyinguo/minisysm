<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { navigationEntries } from '@/utils/workspaceNavigation'
const router = useRouter()
const store = useUserStore()
const selected = ref<string>()
const entries = computed(() => navigationEntries(store.menus || [], path => {
  const match = router.resolve(path)
  return match.matched.length > 0 && match.name !== 'NotFound'
}))
function navigate(path: string) {
  if (entries.value.some(entry => entry.path === path)) void router.push(path)
  selected.value = undefined
}
</script>
<template>
  <el-select v-model="selected" class="navigation-search" filterable clearable aria-label="搜索功能" placeholder="搜索功能，如客户、采购、付款" no-match-text="没有匹配的功能，请换个关键词" no-data-text="暂无可用菜单入口" @change="navigate">
    <template #prefix><el-icon><Search /></el-icon></template>
    <el-option v-for="entry in entries" :key="entry.path" :value="entry.path" :label="[entry.group, entry.label].filter(Boolean).join(' / ')">
      <span class="navigation-search__label">{{ entry.label }}</span><span class="navigation-search__group">{{ entry.group }}</span>
    </el-option>
  </el-select>
</template>
<style scoped>
.navigation-search{width:340px;max-width:36vw}.navigation-search__label{color:#26344a}.navigation-search__group{color:#8a95a6;font-size:12px;margin-left:16px}
@media(max-width:720px){.navigation-search{width:210px;max-width:42vw}}
</style>
