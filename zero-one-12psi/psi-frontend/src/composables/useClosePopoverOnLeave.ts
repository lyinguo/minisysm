import { nextTick, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

/** 路由离开前关闭 popover/dialog，避免 Element Plus 弹层残留导致 Vue 卸载崩溃 */
export function useClosePopoverOnLeave(...visibles: Ref<boolean>[]) {
  onBeforeRouteLeave(async () => {
    visibles.forEach((v) => {
      v.value = false
    })
    await nextTick()
    return true
  })
}
