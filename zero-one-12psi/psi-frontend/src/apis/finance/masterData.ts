import { CustomerAPI } from '@/apis/basicdata/customer'
import { SupplierAPI } from '@/apis/basicdata/supplier'
import { AccountAPI } from '@/apis/basicdata/account'
import { getPersonnelList } from '@/apis/advancedSettings/people'

export type CustomerOption = {
  客户名称: string
  客户编号: string
  客户类别: string
  客户等级: string
  所属组织: string
  备注信息: string
  id: string
}

export type SupplierOption = {
  供应商名称: string
  供应商编号: string
  所属组织: string
  备注信息: string
  id: string
}

export type AccountOption = {
  账户名称: string
  账户编号: string
  所属组织: string
  账户余额: number
  备注信息: string
  id: string
}

export type PeopleOption = {
  人员名称: string
  人员编号: string
  所属组织: string
  人员性别: string
  联系电话: string
  联系地址: string
  身份证号: string
  备注信息: string
  id: string
}

export async function loadCustomerOptions(): Promise<CustomerOption[]> {
  const res = await CustomerAPI.getCustomerList({ pageIndex: 1, pageSize: 200 })
  const rows = res?.code === 10000 && Array.isArray(res.data?.rows) ? res.data.rows : []
  return rows.map((row) => {
    const item = row as unknown as Record<string, unknown>
    return {
      id: String(item.id ?? ''),
      客户名称: String(item.name ?? ''),
      客户编号: String(item.number ?? item.id ?? ''),
      客户类别: String(item.category ?? ''),
      客户等级: String(item.grade ?? ''),
      所属组织: String(item.frame ?? item.username ?? ''),
      备注信息: String(item.memo ?? item.data ?? '')
    }
  })
}

export async function loadSupplierOptions(): Promise<SupplierOption[]> {
  const res = await SupplierAPI.getSupplierList({ pageIndex: 1, pageSize: 200 })
  const rows = res?.code === 10000 && Array.isArray(res.data?.rows) ? res.data.rows : []
  return rows.map((row) => {
    const item = row as unknown as Record<string, unknown>
    return {
      id: String(item.id ?? ''),
      供应商名称: String(item.name ?? ''),
      供应商编号: String(item.number ?? item.code ?? item.id ?? ''),
      所属组织: String(item.frame ?? ''),
      备注信息: String(item.remark ?? item.data ?? '')
    }
  })
}

export async function loadAccountOptions(): Promise<AccountOption[]> {
  const res = await AccountAPI.getAccountList({ pageIndex: 1, pageSize: 200 })
  const rows = res?.code === 10000 && Array.isArray(res.data?.rows) ? res.data.rows : []
  return rows.map((item: Record<string, unknown>) => ({
    id: String(item.id ?? item.number ?? ''),
    账户名称: String(item.name ?? item.accountname ?? ''),
    账户编号: String(item.number ?? item.accountnumber ?? item.id ?? ''),
    所属组织: String(item.frame ?? ''),
    账户余额: Number(item.balance) || 0,
    备注信息: String(item.data ?? '')
  }))
}

export async function loadPeopleOptions(): Promise<PeopleOption[]> {
  try {
    const res = await getPersonnelList({ pageIndex: 1, pageSize: 200 })
    const rows =
      (res as any)?.code === 10000 && Array.isArray((res as any)?.data?.rows)
        ? (res as any).data.rows
        : Array.isArray((res as any)?.data)
          ? (res as any).data
          : []
    return rows.map((item: Record<string, unknown>) => ({
      id: String(item.id ?? ''),
      人员名称: String(item.name ?? ''),
      人员编号: String(item.number ?? item.id ?? ''),
      所属组织: String(item.frame ?? ''),
      人员性别: String(item.sex ?? ''),
      联系电话: String(item.tel ?? ''),
      联系地址: String(item.add ?? item.address ?? ''),
      身份证号: String(item.card ?? ''),
      备注信息: String(item.data ?? '')
    }))
  } catch {
    return []
  }
}
