<template>
  <div class="frame area user-manage">
    <div class="user-toolbar">
      <div><strong>用户列表</strong><span class="result-count">共 {{ page.total }} 条结果</span></div>
      <div class="toolbar-actions"><el-button @click="handleRefresh">刷新列表</el-button><el-button type="primary" :icon="Plus" @click="openDialogForAdd">新增用户</el-button></div>
    </div>
    <el-form class="user-filters" :model="searchForm" @submit.prevent="handleSearch">
      <el-form-item label="用户名称"><el-input v-model="searchForm.name" placeholder="输入姓名或名称" clearable /></el-form-item>
      <el-form-item label="登录账号"><el-input v-model="searchForm.username" placeholder="输入登录账号" clearable /></el-form-item>
      <el-form-item label="手机号码"><el-input v-model="searchForm.tel" placeholder="输入手机号" clearable /></el-form-item>
      <el-form-item label="备注"><el-input v-model="searchForm.remark" placeholder="输入备注关键词" clearable /></el-form-item>
      <div class="user-filter-actions"><el-button type="primary" :icon="Search" native-type="submit">查询</el-button><el-button @click="handleResetSearch">重置条件</el-button></div>
    </el-form>
    <div class="user-table-wrap">
    <!-- 用户数据表格 -->
    <el-table :data="tableRows" height="100%" stripe v-loading="loading" empty-text="没有符合条件的用户，可重置条件或新增用户">
      <el-table-column prop="name" label="用户名称" align="center" width="160" />
      <el-table-column prop="orgName" label="所属组织" align="center" width="160" />
      <el-table-column prop="roleName" label="用户角色" align="center" width="160" />
      <el-table-column prop="username" label="用户账号" align="center" width="160" />
      <el-table-column prop="tel" label="手机号码" align="center" width="160" />
      <el-table-column prop="remark" label="备注信息" align="center" />
      <el-table-column label="相关操作" align="center" width="180">
        <template #default="{ row }">
          <el-button-group>
            <el-button size="small" type="primary" @click="openDialogForEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    </div>

    <!-- 分页组件 -->
    <el-pagination
      class="tablePagination"
      :current-page="page.current"
      :total="page.total"
      :page-size="page.size"
      :page-sizes="page.sizes"
      :pager-count="page.count"
      @size-change="onPageSizeChange"
      @current-change="onPageChange"
      layout="prev,pager,next,jumper,sizes,total"
    />

    <!-- 用户详情/新增对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px" :close-on-click-modal="false">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入用户名称" />
        </el-form-item>
        <!-- 非编辑自身时才显示组织和角色选择 -->
        <el-form-item v-if="!isEditingSelf" label="所属组织" prop="orgId">
          <el-tree-select
            v-model="form.orgId"
            :data="orgTree"
            :props="treeSelectProps"
            placeholder="请选择所属组织"
            style="width: 100%"
            check-strictly
            @change="onOrgChange"
          />
        </el-form-item>
        <el-form-item v-if="!isEditingSelf && form.orgId" label="用户角色" prop="roleId">
          <el-select v-model="form.roleId" placeholder="请选择用户角色" style="width:100%">
            <el-option v-for="r in roleNameList" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户账号" prop="username">
          <el-input v-model="form.username" placeholder="设置用于登录的账号" :disabled="Boolean(form.id)" />
          <span v-if="form.id" class="field-hint">账号用于关联历史业务，创建后不能修改。</span>
        </el-form-item>
        <el-form-item label="手机号码" prop="tel">
          <el-input v-model="form.tel" placeholder="请输入手机号码" />
        </el-form-item>
        <el-form-item label="用户密码" prop="pwd">
          <el-input v-model="form.pwd" type="password" show-password :placeholder="form.id ? '不修改密码请留空' : '设置初始登录密码'" />
          <span class="field-hint">{{ form.id ? '留空会保留原密码；填写新密码后需要使用新密码登录。' : '新用户需要初始密码，请妥善交付给账号使用者。' }}</span>
        </el-form-item>
        <el-form-item label="用户头像" prop="avatar">
          <el-upload :http-request="handleAvatarUpload" accept="image/png,image/jpeg" :show-file-list="false" :disabled="saving || uploadingAvatar">
            <img v-if="form.avatar" :src="form.avatar" class="userAvatar" />
            <div v-else class="avatar-upload-placeholder"><el-icon><Plus /></el-icon><span>选择头像</span></div>
          </el-upload>
          <span class="field-hint">可选，支持 PNG / JPEG，最大 5 MB；上传后请保存用户。</span>
        </el-form-item>
        <el-form-item label="备注信息">
          <el-input v-model="form.remark" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="uploadingAvatar" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import { Plus, Search } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { uploadAvatar, loadAvatar } from '@/apis/advancedSettings/user/avatar'
import {
  getUserList,
  getUserDetail,
  addUser,
  modifyUser,
  deleteUser
} from '@/apis/advancedSettings/user'
import { getOrganizationTree } from '@/apis/advancedSettings/organization'
import { getRoleNameList } from '@/apis/advancedSettings/userrole'
import type { UserAddDTO, UserModDTO } from '@/apis/advancedSettings/user/type'

// 搜索表单数据
const searchForm = reactive({
  name: '',
  username: '',
  tel: '',
  remark: ''
})

// 分页配置
const page = reactive({
  current: 1,
  total: 0,
  size: 30,
  sizes: [30, 60, 90, 150, 300],
  count: 5
})

// 表格数据和加载状态
const tableRows = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)

// 对话框状态
const dialogVisible = ref(false)
const dialogTitle = ref('新增用户')
const formRef = ref<FormInstance>()

// 表单数据
const form = reactive<any>({
  id: '',
  name: '',
  orgId: '',
  roleId: '',
  username: '',
  tel: '',
  pwd: '',
  avatar: '',
  avatarId: '',
  remark: ''
})

// 组织树和角色列表数据
const orgTree = ref<any[]>([])
const roleNameList = ref<any[]>([])
const uploadingAvatar = ref(false)
let avatarObjectUrl = ''
const releaseAvatar = () => {
  if (avatarObjectUrl) URL.revokeObjectURL(avatarObjectUrl)
  avatarObjectUrl = ''
}
onBeforeUnmount(releaseAvatar)

// 组织映射表 (用于将组织ID转换为组织名称)
const orgMap = ref<Record<string, string>>({})

// 树形选择器配置
const treeSelectProps = {
  value: 'id',
  label: 'name',
  children: 'children'
}

// 表单验证规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入用户名称', trigger: 'blur' }],
  orgId: [{ required: true, message: '请选择所属组织', trigger: 'change' }],
  roleId: [{ required: true, message: '请选择用户角色', trigger: 'change' }],
  username: [{ required: true, message: '请输入用户账号', trigger: 'blur' }],
  tel: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    {
      validator: (_r, v, cb) => {
        /^1\d{10}$/.test(v) ? cb() : cb(new Error('请输入以 1 开头的 11 位手机号码'))
      },
      trigger: 'blur'
    }
  ]
}

// 计算属性：判断是否正在编辑自身账户
const isEditingSelf = computed(() => false)

/**
 * 构建组织映射表
 */
const buildOrgMap = (orgs: any[]) => {
  orgs.forEach(org => {
    orgMap.value[org.id] = org.name
    if (org.children && org.children.length > 0) {
      buildOrgMap(org.children)
    }
  })
}

/**
 * 获取组织名称
 */
const getOrgName = (orgId: string): string => {
  return orgMap.value[orgId] || orgId
}

/**
 * 获取用户列表
 * @param goFirst 是否跳转到第一页
 */
const fetchUsers = (goFirst?: number): Promise<void> => {
  loading.value = true
  if (goFirst === 1) page.current = 1

  const params: any = {
    pageIndex: page.current,
    pageSize: page.size
  }

  if (searchForm.name) params.name = searchForm.name
  if (searchForm.username) params.user = searchForm.username
  if (searchForm.tel) params.tel = searchForm.tel
  if (searchForm.remark) params.data = searchForm.remark

  return getUserList(params).then((res): void => {
    if (res.code === 10000 && res.data) {

      tableRows.value = (res.data.rows || []).map((u: any) => {

        const userId = u.id

        return {
          id: userId,
          ...u,
          orgName: getOrgName(u.frame) || u.frame, // 使用组织名称，如果没有映射则显示ID
          roleName: roleNameList.value.find(role => String(role.id) === String(u.role))?.name || u.role || '',
          username: u.user || '',
          remark: u.data || ''
        }
      })

      page.total = res.data.total || 0

      if (tableRows.value.length === 0 && (searchForm.name || searchForm.username || searchForm.tel || searchForm.remark)) {
        ElMessage.info('未找到符合条件的用户')
      }
    } else {
      ElMessage.error(res.message || '获取用户列表失败')
    }
  }).catch((err): void => {
    console.error('获取用户列表失败:', err)
    ElMessage.error('获取用户列表失败')
  }).finally(() => {
    loading.value = false
  })
}

/**
 * 处理搜索
 */
const handleSearch = () => {
  fetchUsers(1)
}

/**
 * 重置搜索条件
 */
const handleResetSearch = () => {
  Object.assign(searchForm, { name: '', username: '', tel: '', remark: '' })
  fetchUsers(1)
}

/**
 * 获取组织树数据
 */
const fetchOrgTree = () => {
  return getOrganizationTree().then(res => {
    if (res.code === 10000) {
      orgTree.value = res.data || []
      // 构建组织映射表
      buildOrgMap(orgTree.value)
    } else {
      ElMessage.error('获取组织树失败: ' + (res.message || '未知错误'))
    }
  }).catch(err => {
    console.error('获取组织树失败:', err)
    ElMessage.error('获取组织树失败')
  })
}

/**
 * 获取角色列表数据
 */
const fetchRoleNames = () => {
  return getRoleNameList().then(res => {
    if (res.code === 10000 && res.data && res.data.roleNameList) {
      roleNameList.value = res.data.roleNameList || []
    }
  }).catch(err => {
    console.error('获取角色列表失败:', err)
  })
}

/**
 * 检查组织ID是否存在
 */
const checkOrgExists = (orgId: string): boolean => {
  const findOrg = (orgs: any[]): boolean => {
    for (const org of orgs) {
      if (org.id === orgId) return true
      if (org.children && org.children.length > 0) {
        if (findOrg(org.children)) return true
      }
    }
    return false
  }

  return findOrg(orgTree.value)
}

/**
 * 组织选择变更事件
 */
const onOrgChange = (orgId: string) => {

  // 重置角色选择（因为角色可能依赖于组织）
  form.roleId = ''
}

/**
 * 打开新增用户对话框
 */
const openDialogForAdd = () => {
  formRef.value?.clearValidate()
  releaseAvatar()
  dialogTitle.value = '新增用户'
  Object.assign(form, {
    id: '',
    name: '',
    orgId: '',
    roleId: '',
    username: '',
    tel: '',
    pwd: '',
    avatar: '',
    avatarId: '',
    remark: ''
  })
  dialogVisible.value = true
}

/**
 * 打开编辑用户对话框
 * @param row 用户数据行
 */
const openDialogForEdit = (row: any) => {

  //if (!row.id) {
    //ElMessage.error('用户ID不存在，无法获取详情')
    //return
  //}

  dialogTitle.value = '编辑用户'
  getUserDetail(row.id).then(async res => {
    if (res.code === 10000 && res.data) {
      const d: any = res.data
      releaseAvatar()
      Object.assign(form, {
        id: row.id,
        name: d.name || '',
        orgId: d.frame || '',
        roleId: d.role || '',
        username: d.user || '',
        tel: d.tel || '',
        pwd: '',
        avatar: d.imgUrl || d.img || '',
        avatarId: d.img || '',
        remark: d.data || ''
      })
      formRef.value?.clearValidate()
      dialogVisible.value = true
      if (form.avatarId) {
        try {
          const url = await loadAvatar(form.avatarId)
          if (form.id === row.id && dialogVisible.value) { avatarObjectUrl = url; form.avatar = url }
          else URL.revokeObjectURL(url)
        } catch { /* Existing FastDFS avatars retain their original preview URL. */ }
      }
    } else {
      ElMessage.error(res.message || '获取用户详情失败')
    }
  }).catch(err => {
    console.error('获取用户详情失败:', err)
    ElMessage.error('获取用户详情失败')
  })
}

/**
 * 提交表单（新增或修改用户）
 */
const handleSubmit = async () => {
  if (saving.value || uploadingAvatar.value || !formRef.value) return
  saving.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    if (!checkOrgExists(form.orgId)) { ElMessage.error('选择的组织不存在，请重新选择'); return }
    if (!roleNameList.value.some(role => String(role.id) === String(form.roleId))) {
      ElMessage.error('选择的角色不存在，请重新选择')
      return
    }
    const editing = Boolean(form.id)
    if (!editing && !form.pwd) { ElMessage.error('请输入用户密码'); return }
    const payload: UserAddDTO = {
      name: form.name.trim(), frame: form.orgId, role: form.roleId,
      user: form.username.trim(), tel: form.tel.trim(), pwd: form.pwd || undefined,
      img: form.avatarId || undefined, data: form.remark ?? ''
    }
    const result = editing
      ? await modifyUser({ ...payload, id: form.id })
      : await addUser(payload)
    if (result?.code !== 10000) throw new Error(result?.message || '用户保存失败')
    form.pwd = ''
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await fetchUsers()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    saving.value = false
  }
}

/**
 * 删除用户
 * @param row 用户数据行
 */
const handleDelete = (row: any) => {
  ElMessageBox.confirm('您确定要删除该用户吗？', '提示', { type: 'warning' })
    .then(() => deleteUser(row.id))
    .then(res => {
      if (res && res.code === 10000) {
        ElMessage.success('删除成功')
        fetchUsers()
      } else {
        ElMessage.error(res?.message || '删除失败')
      }
    })
    .catch(() => {})
}

/**
 * 刷新用户列表
 */
const handleRefresh = () => fetchUsers()

/**
 * 分页大小改变事件
 * @param size 新的分页大小
 */
const onPageSizeChange = (size: number) => {
  page.size = size;
  fetchUsers(1)
}

/**
 * 页码改变事件
 * @param p 新的页码
 */
const onPageChange = (p: number) => {
  page.current = p;
  fetchUsers()
}

/**
 * 头像上传成功回调
 * @param result 上传结果
 */
const handleAvatarUpload = async (options: UploadRequestOptions) => {
  if (uploadingAvatar.value) return
  if (options.file.size > 5 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(options.file.type)) {
    ElMessage.error('请选择不超过5MB的PNG或JPEG图片')
    return
  }
  uploadingAvatar.value = true
  try {
    const result = await uploadAvatar(options.file)
    const url = await loadAvatar(result.id)
    releaseAvatar()
    avatarObjectUrl = url
    form.avatarId = result.id
    form.avatar = url
    ElMessage.success('头像已上传，请保存用户信息')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally { uploadingAvatar.value = false }
}

// 页面加载时初始化数据
onMounted(() => {
  // 先加载组织树和角色列表，然后加载用户列表
  Promise.all([fetchOrgTree(), fetchRoleNames()]).then(() => {
    fetchUsers(1)
  })
})
</script>



<style scoped>
.user-manage{overflow:visible}.user-filters :deep(.el-form-item__label){text-align:left}
@media(max-width:600px){.user-manage{height:auto;min-height:0}.user-table-wrap{height:360px;flex:none}.tablePagination{justify-content:flex-start}}
</style>

<style scoped>
.user-manage{display:flex;flex-direction:column;gap:18px;min-height:460px}.user-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;flex:none}.user-toolbar strong{font-size:15px;font-weight:600;color:#26344a}.result-count{font-size:12px;color:#8490a3;margin-left:12px}.toolbar-actions{display:flex;gap:10px}.toolbar-actions .el-button+.el-button{margin-left:0}
.user-filters{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr)) auto;gap:14px;padding:16px;background:#f7f9fd;border:1px solid #edf1f7;border-radius:9px;align-items:end;flex:none}.user-filters :deep(.el-form-item){display:block;margin:0}.user-filters :deep(.el-form-item__label){float:none;height:auto;line-height:1.5;display:block;padding-bottom:7px;font-size:12px}.user-filter-actions{display:flex;gap:8px;padding-bottom:1px}.user-filter-actions .el-button+.el-button{margin-left:0}.user-table-wrap{flex:1;min-height:240px}.tablePagination{flex:none;margin-top:0;padding-top:0}.field-hint{display:block;width:100%;font-size:12px;color:#8490a3;line-height:1.7;margin-top:5px}.avatar-upload-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;width:100px;height:100px;border:1px dashed #c9d5e8;border-radius:10px;color:#71829c;background:#f9fbff;font-size:12px}.avatar-upload-placeholder .el-icon{font-size:24px}
@media(max-width:1180px){.user-filters{grid-template-columns:repeat(2,minmax(130px,1fr))}.user-filter-actions{grid-column:1 / -1}.user-manage{min-height:540px}}@media(max-width:600px){.user-filters{grid-template-columns:1fr;gap:10px}.user-manage{height:auto;min-height:0}.toolbar-actions{gap:6px}}
</style>

<style scoped>.userAvatar{width:100px;height:100px;display:block;object-fit:cover;border-radius:10px}@media(max-width:600px){.user-table-wrap{height:360px;flex:none}}</style>
