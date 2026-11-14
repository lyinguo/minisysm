import { nextTick } from 'vue'
import type { FormInstance, FormItemRule } from 'element-plus'

/** 表单校验结果（含首个错误字段，便于定位与提示） */
export interface FormValidateResult {
  valid: boolean
  message?: string
  field?: string
}

/** 生成「如：xxx」形式的占位提示，仅在输入框为空时显示 */
export function examplePlaceholder(example: string, prefix = '如：'): string {
  return `${prefix}${example}`
}

/** 去除首尾空白，空字符串返回 undefined */
export function trimOrUndefined(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return trimmed || undefined
}

/** 必填文本（失焦即校验） */
export function requiredText(message: string, trigger: FormItemRule['trigger'] = 'blur'): FormItemRule {
  return {
    required: true,
    message,
    trigger,
    transform: (value) => (typeof value === 'string' ? value.trim() : value)
  }
}

/** 正整数（排序等） */
export function positiveInt(message = '请输入正整数', trigger: FormItemRule['trigger'] = 'change'): FormItemRule {
  return {
    required: true,
    trigger,
    validator: (_rule, value, callback) => {
      const num = Number(value)
      if (!Number.isInteger(num) || num < 1) {
        callback(new Error(message))
        return
      }
      callback()
    }
  }
}

/** 数组至少一项（如辅助属性的属性内容） */
export function arrayNotEmpty(message: string, trigger: FormItemRule['trigger'] = 'change'): FormItemRule {
  return {
    required: true,
    trigger,
    validator: (_rule, value, callback) => {
      if (!Array.isArray(value) || value.length === 0) {
        callback(new Error(message))
        return
      }
      callback()
    }
  }
}

/** 列表项 name 去重校验（校验 form 字段 value） */
export function uniqueNamesRule(message = '内容不能重复'): FormItemRule {
  return {
    trigger: 'change',
    validator: (_rule, value, callback) => {
      if (!Array.isArray(value)) {
        callback()
        return
      }
      const names = value
        .map((item: { name?: string }) => (item.name || '').trim())
        .filter(Boolean)
      const unique = new Set(names)
      if (names.length !== unique.size) {
        callback(new Error(message))
        return
      }
      callback()
    }
  }
}

/** 从 Element Plus 校验失败对象中提取第一条错误文案 */
export function getFirstInvalidFieldMessage(invalidFields: unknown): string | undefined {
  if (!invalidFields || typeof invalidFields !== 'object') return undefined
  const record = invalidFields as Record<string, Array<{ message?: string }>>
  for (const key of Object.keys(record)) {
    const message = record[key]?.[0]?.message
    if (message) return message
  }
  return undefined
}

/** 从 Element Plus 校验失败对象中提取首个错误字段 prop */
export function getFirstInvalidFieldProp(invalidFields: unknown): string | undefined {
  if (!invalidFields || typeof invalidFields !== 'object') return undefined
  const keys = Object.keys(invalidFields as object)
  return keys[0]
}

/** 滚动到容器内第一个校验失败的表单项，并尝试聚焦可编辑控件 */
export function scrollToFirstFormError(container?: HTMLElement | null) {
  const scope = container ?? document.body
  const errorItem =
    scope.querySelector('.el-form-item.is-error') ??
    document.querySelector('.el-form-item.is-error')

  if (!(errorItem instanceof HTMLElement)) return

  errorItem.scrollIntoView({ behavior: 'smooth', block: 'center' })

  const focusable = errorItem.querySelector<HTMLElement>(
    'input:not([type="hidden"]), textarea, .el-select__wrapper, .el-input__wrapper'
  )
  if (focusable instanceof HTMLElement) {
    focusable.focus({ preventScroll: true })
  }
}

/** 校验表单：失败时标红字段、滚动定位，并返回首个错误信息 */
export async function validateFormWithFocus(
  formRef: FormInstance | undefined,
  container?: HTMLElement | null
): Promise<FormValidateResult> {
  if (!formRef) return { valid: true }

  try {
    await formRef.validate()
    return { valid: true }
  } catch (invalidFields) {
    await nextTick()
    scrollToFirstFormError(container)
    return {
      valid: false,
      field: getFirstInvalidFieldProp(invalidFields),
      message: getFirstInvalidFieldMessage(invalidFields)
    }
  }
}

/** 从接口响应中提取可读错误信息 */
export function extractApiErrorMessage(error: unknown, fallback = '操作失败'): string {
  if (!error || typeof error !== 'object') return fallback
  const res = error as { data?: { data?: unknown; message?: string }; message?: string }
  if (typeof res.data?.data === 'string' && res.data.data.trim()) {
    return res.data.data
  }
  if (typeof res.data?.message === 'string' && res.data.message.trim()) {
    return res.data.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

/** 判断错误是否已被 http 拦截器提示过 */
export function isHttpHandledError(error: unknown): boolean {
  return !!(error && typeof error === 'object' && 'data' in error)
}

/** 判断字符串是否仅含 ASCII 字符（条形码要求） */
export function isAsciiString(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    if (value.charCodeAt(i) > 127) return false
  }
  return true
}

/** 条码内容校验：条形码仅 ASCII，二维码可含中文 */
export function barcodeInfoRule(getType: () => number): FormItemRule {
  return {
    trigger: ['blur', 'change'],
    validator: (_rule, value, callback) => {
      const text = typeof value === 'string' ? value.trim() : ''
      if (!text) {
        callback(new Error('请输入条码内容'))
        return
      }
      if (getType() === 0 && !isAsciiString(text)) {
        callback(new Error('条形码仅支持英文、数字及符号，不能包含中文'))
        return
      }
      callback()
    }
  }
}

/** 创建条码表单规则（随类型动态校验内容） */
export function createBarcodeFormRules(getType: () => number) {
  return {
    name: [requiredText('请输入条码名称，如：仓库货架标识')],
    info: [barcodeInfoRule(getType)],
    type: [{ required: true, message: '请选择条码类型', trigger: 'change' }]
  }
}

/** 根据条码类型返回内容占位示例 */
export function barcodeInfoPlaceholder(type: number): string {
  return type === 0 ? examplePlaceholder('WH-001-A01') : examplePlaceholder('产品编号-2024-001')
}

/** 辅助属性模块常用字段规则 */
export const attributeFormRules = {
  name: [requiredText('请输入属性名称，如：颜色、尺码')],
  sort: [positiveInt('排序必须为正整数，如：1')],
  content: [arrayNotEmpty('请至少添加一项属性内容，如：红色、蓝色')]
}

/** 收支类别常用字段规则 */
export const incomeCategoryFormRules = {
  name: [
    requiredText('请输入收支名称，如：运费收入'),
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  type: [{ required: true, message: '请选择收支类型', trigger: 'change' }],
  sort: [positiveInt('排序范围 1-999', 'change')]
}
