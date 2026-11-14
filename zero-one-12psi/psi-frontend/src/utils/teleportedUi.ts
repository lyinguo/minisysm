/**
 * 导航完成后再清理可能残留的报表搜索弹层（切勿在 beforeEach / onBeforeRouteLeave 中调用）。
 * 只删带 searchPopover 类名的 popper，不删 el-overlay，避免打断 Vue 卸载流程。
 */
export function cleanupReportSearchPopups() {
  document.querySelectorAll('body > .el-popper.searchPopover').forEach((node) => {
    if (node.parentNode) {
      node.parentNode.removeChild(node)
    }
  })
}
