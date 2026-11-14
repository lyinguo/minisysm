<template>
  <div class="header-row">
    <!-- 应用信息栏 -->
    <div class="header-title">
      <img v-show="!isCollapse" class="app-icon" src="/logo.jpg" :title="appName" />
      <el-text v-show="!isCollapse" class="app-name">{{ appName }}</el-text>
      <el-button
        v-show="isCollapse"
        link
        class="collapse-btn"
        icon="IconExpand"
        @click="isCollapse = !isCollapse"
      ></el-button>
      <el-button
        v-show="!isCollapse"
        link
        class="collapse-btn"
        icon="IconFold"
        @click="isCollapse = !isCollapse"
      ></el-button>
    </div>
    <!-- 导航栏 -->
    <div class="header-nav">
      <el-tooltip content="刷新Token" effect="light" placement="bottom">
        <el-button link class="nav-btn" @click="handleReload">
          <el-icon size="18">
            <IconReset />
          </el-icon>
        </el-button>
      </el-tooltip>
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-dropdown">
          <el-avatar :size="30" :src="user?.avatar" />
          <span class="user-name">{{ user?.username || '游客' }}</span>
          <el-icon class="el-icon--right">
            <ArrowDown />
          </el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout" divided>
              <el-icon>
                <IconSwitchButton />
              </el-icon>
              <span style="margin-left: 8px">退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
  <div class="content-row">
    <!-- 侧边菜单栏 -->
    <el-menu
      :collapse="isCollapse"
      :default-active="menuActivePath"
      active-text-color="#409EFF"
      text-color="#fff"
      background-color="#545c64"
      unique-opened
      :collapse-transition="false"
      @select="handleMenuSelect"
    >
      <el-menu-item :index="indexPath">
        <el-icon>
          <IconHomeFilled />
        </el-icon>
        <span>首页</span>
      </el-menu-item>
      <!-- 菜单为空时的提示 -->
      <el-menu-item v-if="menus.length === 0" disabled>
        <el-icon>
          <IconWarning />
        </el-icon>
        <span style="color: #909399; font-size: 12px">暂无菜单权限</span>
      </el-menu-item>

      <el-sub-menu v-for="item in menus" :key="item.id" :index="item.id + 'submenu'">
        <template #title>
          <el-icon>
            <component :is="useRenderIcon(item.icon)" />
          </el-icon>
          <span>{{ item.text }}</span>
        </template>

        <el-menu-item-group>
          <!-- 处理二级菜单项 -->
          <template v-for="i in item.children" :key="i.id">
            <!-- 如果有三级子菜单，渲染为 sub-menu -->
            <el-sub-menu v-if="i.children && i.children.length > 0" :index="i.id + 'submenu'">
              <template #title>
                <div class="sub-menu-title">
                  <div class="sub-menu-title-left">
                    <el-icon>
                      <component :is="useRenderIcon(i.icon)" />
                    </el-icon>
                    <span>{{ i.text }}</span>
                  </div>
                  <el-button
                    v-if="i.hasReport"
                    class="sub-menu-report-btn"
                    type="primary"
                    size="small"
                    text
                    @click.stop="openReport(i)"
                  >
                    报表
                  </el-button>
                </div>
              </template>

              <!-- 三级菜单项 -->
              <el-menu-item
                v-for="j in i.children"
                :key="j.id"
                :index="j.href || ''"
                :disabled="!isNavigableMenuPath(j.href)"
              >
                <el-icon>
                  <component :is="useRenderIcon(j.icon)" />
                </el-icon>
                {{ j.text }}
              </el-menu-item>
            </el-sub-menu>

            <!-- 如果没有子菜单，直接渲染为 menu-item -->
            <el-menu-item
              v-else
              :index="i.href || ''"
              :disabled="!isNavigableMenuPath(i.href)"
              :class="i.hideReport ? 'menu-item-centered' : 'menu-item-with-report'"
            >
              <div class="menu-item-content">
                <div class="menu-item-left">
                  <el-icon>
                    <component :is="useRenderIcon(i.icon)" />
                  </el-icon>
                  <span>{{ i.text }}</span>
                </div>
                <el-button
                  v-if="i.hasReport"
                  class="report-btn"
                  type="primary"
                  size="small"
                  text
                  @click.stop="openReport(i)"
                >
                  报表
                </el-button>
              </div>
            </el-menu-item>
          </template>
        </el-menu-item-group>
      </el-sub-menu>
    </el-menu>
    <!-- 主内容区 -->
    <div class="main">
      <!-- 标签栏 -->
      <el-tabs
        :model-value="route.path"
        type="border-card"
        :before-leave="beforeLeave"
        @tab-click="onTabClick"
        @tab-remove="tabColse"
      >
        <!-- 首页标签页 -->
        <el-tab-pane :name="indexPath" style="height: 0">
          <template #label>
            <el-icon>
              <IconHomeFilled />
            </el-icon>
            <span style="padding-left: 5px">首页</span>
          </template>
        </el-tab-pane>

        <!-- 动态标签页 -->
        <el-tab-pane
          v-for="item in tabs"
          :key="item.path"
          :label="item.label"
          :name="item.path"
          closable
          style="height: 0"
        />

        <!-- 操作标签页 -->
        <el-tab-pane style="height: 0" name="tab-operation">
          <template #label>
            <el-dropdown trigger="click">
              <el-button class="operation-icon" type="info" link>
                <el-icon size="22">
                  <IconOperation />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    :disabled="tabs.length == 0"
                    icon="IconCloseBlod"
                    @click="handleClose(1)"
                  >
                    关闭所有标签页
                  </el-dropdown-item>
                  <el-dropdown-item
                    :disabled="route.path == indexPath || tabstore.getTabIndex(route.path) == 0"
                    icon="IconCloseBlod"
                    @click="handleClose(2)"
                  >
                    关闭当前标签页左边
                  </el-dropdown-item>
                  <el-dropdown-item
                    :disabled="tabstore.getTabIndex(route.path) == tabs.length - 1"
                    icon="IconCloseBlod"
                    @click="handleClose(3)"
                  >
                    关闭当前标签页右边
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-tab-pane>
      </el-tabs>

      <!-- 由 RouterView 管理组件实例和路由离开守卫。 -->
      <div class="routerPage">
        <router-view v-slot="{ Component, route: pageRoute }">
          <RoutePageBoundary :key="`${pageRoute.fullPath}-${viewKey}`">
            <component :is="Component" />
          </RoutePageBoundary>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { useTabStore } from '@/stores/tab'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import type { TabPaneName, TabsPaneContext } from 'element-plus'
import type { Menu } from '@/apis/login/type'
import { useRenderIcon } from '@/components/ReIcon/src/hooks'
import RoutePageBoundary from '@/components/RoutePageBoundary.vue'
// 应用名称
const appName = import.meta.env.VITE_APP_TITLE
// 当前用户信息
const ustore = useUserStore()
// 用户信息提示
const { user, menus } = storeToRefs(ustore)
const userInfo = ref('欢迎用户：' + (user.value === null ? '游客' : user.value.username))
// 菜单是是否折叠
const isCollapse = ref(false)
// 监听菜单变化，如果菜单为空则提示用户
const hasShownEmptyMenuWarning = ref(false)
watch(
  menus,
  (newMenus) => {
    // 只在菜单加载完成且为空时提示一次
    if (newMenus.length === 0 && ustore.isLoaded && !hasShownEmptyMenuWarning.value) {
      ElMessage.warning({
        message: '当前用户暂无菜单权限，请联系管理员分配权限',
        duration: 5000
      })
      hasShownEmptyMenuWarning.value = true
    }
  },
  { immediate: true }
)
// 路由数据
const router = useRouter()
const route = useRoute()
// 标签页数据
const tabstore = useTabStore()
const { tabs, indexPath, viewKey } = storeToRefs(tabstore)
const menuActivePath = computed(() => route.path)

/** 路由变化后同步 tab 列表 */
watch(
  () => route.fullPath,
  () => {
    const path = route.path
    if (!path) return
    const label = typeof route.meta?.label === 'string' ? route.meta.label : undefined
    tabstore.syncRouteTab(path, label)
  },
  { flush: 'post', immediate: true }
)

function isNavigableMenuPath(href?: string) {
  return Boolean(href && href.startsWith('/') && !href.startsWith('/#'))
}

function navigateFromMenu(path: string) {
  router.push({ path }).catch((err) => {
    if (err?.name === 'NavigationFailure' || String(err?.message || '').includes('No match')) {
      ElMessage.warning(`路由 ${path} 不存在，请检查菜单配置`)
    }
  })
}

/** 点击标签 → 跳转路由 */
function onTabClick(pane: TabsPaneContext) {
  if (pane.paneName === 'tab-operation') return
  const path = String(pane.paneName)
  if (path && path !== route.path) {
    navigateFromMenu(path)
  }
}
/** 标签页关闭事件 */
const tabColse = (name: TabPaneName) => {
  if (route.path === name) {
    const idx = tabstore.getTabIndex(name as string) - 1
    const nextPath = idx >= 0 ? tabs.value[idx].path : indexPath.value
    navigateFromMenu(nextPath)
  }
  tabstore.remTab(name as string)
}
/** 标签页切换事件 */
const beforeLeave = (activeName: TabPaneName) => {
  // 操作标签不做激活操作
  if (activeName == 'tab-operation') return false
  return true
}

/** 管理标签页关闭 */
function handleClose(type: number) {
  switch (type) {
    case 1:
      tabstore.reset()
      router.push({ path: indexPath.value })
      break
    case 2:
      tabstore.remBeforeTab(route.path)
      break
    case 3:
      tabstore.remAfterTab(route.path)
      break
    default:
      break
  }
}

/** 菜单点击 → 跳转路由 */
function handleMenuSelect(index: string) {
  if (!isNavigableMenuPath(index)) return
  if (route.path === index) return

  const resolved = router.resolve(index)
  const label = typeof resolved.meta?.label === 'string' ? resolved.meta.label : undefined
  tabstore.syncRouteTab(index, label)

  navigateFromMenu(index)
}

/** 打开报表页面（单据旁的「报表」快捷按钮） */
function openReport(menuItem: any) {
  const reportPath = menuItem.reportHref || (menuItem.href ? menuItem.href + '-report' : '')
  const reportLabel = menuItem.text + '报表'

  if (!reportPath || !isNavigableMenuPath(reportPath)) {
    ElMessage.warning('无法获取报表路径，请检查菜单配置')
    return
  }

  if (route.path !== reportPath) {
    tabstore.syncRouteTab(reportPath, reportLabel)
    router.push({ path: reportPath }).catch(() => {})
  }
}

/** 刷新token */
async function handleReload() {
  try {
    // 调用 store 的刷新 token 方法
    await ustore.reloadToken()
    // 注意：不在这里调用 loadUser()，因为页面刷新后路由守卫会自动调用
    ElMessage({
      type: 'success',
      message: 'Token刷新成功，正在刷新页面...',
      duration: 1000
    })
    // 延迟一下让用户看到成功消息，然后刷新页面
    // 页面刷新后，路由守卫会自动调用 loadUser() 加载用户信息
    setTimeout(() => {
      window.location.reload()
    }, 500)
  } catch (err) {
    ElMessage({
      type: 'error',
      message: 'Token刷新失败，请重新登录!'
    })
    // 如果刷新失败，跳转到登录页
    router.push({ name: 'Login' })
  }
}

/** 处理下拉菜单命令 */
function handleCommand(command: string) {
  if (command === 'logout') {
    handleLogout()
  }
}

/** 退出登录 */
async function handleLogout() {
  try {
    // 调用 store 的退出登录方法（会自动调用后端接口）
    await ustore.resetSaveData()
    // 跳转到登录页
    router.push({ name: 'Login' })
    ElMessage({
      type: 'success',
      message: '退出登录成功!'
    })
  } catch (err) {
    // 即使后端接口失败，也继续清理前端数据并跳转
    router.push({ name: 'Login' })
    ElMessage({
      type: 'warning',
      message: '退出登录时出现异常，但已清理本地数据'
    })
  }
}
</script>

<style>
:root {
  --home-header-height: 60px;
  --home-menu-width: 220px;
}
.main .el-tabs {
  .el-tabs__header {
    padding: 0;
    margin-bottom: 0;
  }
  .el-tabs__content {
    padding-top: 0px;
    padding-bottom: 0;
  }
  #tab-tab-operation {
    padding: 0;
  }
}
</style>

<style scoped>
.header-row {
  height: var(--home-header-height);
  background-color: #6c777f;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .header-title {
    width: var(--home-menu-width);
    padding-left: 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    .app-icon {
      width: 30px;
      border-radius: 5px;
    }
    .app-name {
      color: white;
      font-size: 16px;
    }

    .collapse-btn {
      color: white;
      font-size: 24px;
    }
  }

  .header-nav {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    padding-right: 15px;
    color: #f8f8f8;
    text-align: right;

    .nav-btn {
      color: #f8f8f8;
      padding: 8px;
    }

    .nav-btn:hover {
      color: #409eff;
    }

    .user-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: #f8f8f8;
      padding: 4px 8px;
      border-radius: 4px;
      transition: background-color 0.3s;

      &:hover {
        background-color: rgba(255, 255, 255, 0.1);
      }

      .user-name {
        font-size: 14px;
      }
    }
  }
}
.content-row {
  height: calc(100vh - var(--home-header-height));
  display: flex;
  flex-direction: row;

  .el-menu {
    border: 0;
    width: var(--home-menu-width);
    height: 100%;
    overflow: auto;
  }

  .el-menu--collapse {
    width: calc(var(--el-menu-icon-width) + var(--el-menu-base-level-padding) * 2);
  }

  .main {
    flex: 1;
    background-color: #edecec;
    width: calc(100vw - var(--home-menu-width));
    height: 100%;
    overflow: auto;

    .operation-icon {
      padding: calc(var(--el-tabs-header-height) / 2 - 12px) 20px;
    }
  }
}
.routerPage {
  position: relative;
  isolation: isolate;
  padding: 12px;
  overflow: auto;
  box-sizing: border-box;
  height: calc(100% - 41px);
  min-height: 0;
}

/* 菜单项报表按钮样式 */
.menu-item-with-report {
  padding: 0 !important;
}

/* 居中显示的菜单项（无报表按钮） */
.menu-item-centered {
  padding: 0 !important;
}

.menu-item-centered .menu-item-content {
  padding-left: 60px;
  justify-content: flex-start;
}

.menu-item-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-left: 40px;
  padding-right: 10px;
}

.menu-item-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.report-btn {
  font-size: 12px;
  padding: 2px 8px;
  height: 24px;
  margin-left: 8px;
  opacity: 0.8;
}

.report-btn:hover {
  opacity: 1;
}

/* 子菜单标题样式 */
.sub-menu-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 10px;
}

.sub-menu-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.sub-menu-report-btn {
  font-size: 12px;
  padding: 2px 8px;
  height: 24px;
  margin-left: 8px;
  opacity: 0.8;
}

.sub-menu-report-btn:hover {
  opacity: 1;
}
</style>
