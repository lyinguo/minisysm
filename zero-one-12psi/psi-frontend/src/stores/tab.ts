import { defineStore } from 'pinia'
import type { TabRoute } from '@/types/Route'

//FIXME 如果主界面首页路径不是/dashboard则需要修改此变量的值
const INDEX_PATH = '/dashboard'

/** 最多同时打开的标签数，超出后关闭最早打开的标签 */
export const MAX_TABS = 15

export const useTabStore = defineStore('tab', {
  state: () => ({
    /**  已经打开的标签页 */
    tabs: [] as Array<TabRoute>,
    /** 当前激活的标签页（与路由 path 对齐） */
    activeIndex: INDEX_PATH,
    /** 首页的标签路径 */
    indexPath: INDEX_PATH,
    /** 主内容区强制刷新计数，用于路由已变但组件未卸载时 */
    viewKey: 0
  }),
  getters: {
    /** 获取已经打开的标签页 */
    getTabs: (state) => state.tabs,
    /** 获取当前激活的标签页 */
    getActiveIndex: (state) => state.activeIndex,
    /** 获取指定标签页索引值 */
    getTabIndex: (state) => (path: string) => {
      return state.tabs.findIndex((item) => item.path === path)
    },
    /** el-tabs 可用的激活项：必须是已存在的 tab 或首页 */
    resolvedActiveTab: (state) => {
      if (state.activeIndex === state.indexPath) return state.indexPath
      if (state.tabs.some((t) => t.path === state.activeIndex)) return state.activeIndex
      return state.indexPath
    }
  },
  actions: {
    /** 添加标签页 */
    addTab(data: TabRoute) {
      if (data.path === this.indexPath) return
      if (this.getTabIndex(data.path) !== -1) return
      this.tabs.push(data)
    },
    /**
     * 路由跳转后同步标签：确保 tab 存在、activeIndex 合法，并 bump viewKey 刷新内容区
     */
    syncRouteTab(path: string, label?: string) {
      if (!path) return

      if (path === this.indexPath) {
        if (this.activeIndex !== path) this.bumpViewKey()
        this.activeIndex = path
        return
      }

      if (label) {
        const idx = this.getTabIndex(path)
        if (idx === -1) {
          while (this.tabs.length >= MAX_TABS) {
            this.tabs.shift()
          }
          this.tabs.push({ path, label })
        } else {
          this.tabs[idx].label = label
        }
      } else if (path !== this.indexPath && this.getTabIndex(path) === -1) {
        while (this.tabs.length >= MAX_TABS) {
          this.tabs.shift()
        }
        this.tabs.push({ path, label: path })
      }

      if (this.activeIndex !== path) {
        this.bumpViewKey()
      }
      this.activeIndex = path
    },
    bumpViewKey() {
      this.viewKey += 1
    },
    /** 删除标签页 */
    remTab(path: string) {
      const index = this.getTabIndex(path)
      if (index == -1) return
      this.tabs.splice(index, 1)
    },
    /** 删除指定标签页前面的标签页 */
    remBeforeTab(path: string) {
      if (path === this.indexPath) return
      const index = this.getTabIndex(path)
      if (index == -1) return
      this.tabs.splice(0, index)
    },
    /** 删除指定标签页后面的标签页 */
    remAfterTab(path: string) {
      if (path === this.indexPath) {
        this.reset()
        return
      }
      const index = this.getTabIndex(path)
      if (index == -1) return
      this.tabs.splice(index + 1)
    },
    /** 设置当前激活的标签页 */
    setActiveIndex(index: string) {
      this.activeIndex = index
    },
    /** 重置数据 */
    reset() {
      this.tabs = []
      this.activeIndex = INDEX_PATH
      this.bumpViewKey()
    }
  }
})
