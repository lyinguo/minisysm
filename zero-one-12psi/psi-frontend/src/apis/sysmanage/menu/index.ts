/*
 * @Description: 系统配置-菜单管理相关接口
 */
import { useHttp, type RequestCallback } from '@/plugins/http'
import { handleJsonRequest } from '@/apis/utils/jsonResponse'
import type { MenuItem, MenuNameTreeVO } from './type'

const currBaseUrl = '/j1-sysc/menu-manager'
const http = useHttp()

export const getMenuList = async (success: RequestCallback, fail: RequestCallback) => {
  return handleJsonRequest(
    http.get<MenuItem[]>(`${currBaseUrl}/query-menuList`, {}, { showLoading: true }),
    success,
    fail
  )
}

export const getMenuTree = async (success: RequestCallback, fail: RequestCallback) => {
  return handleJsonRequest(
    http.get<MenuNameTreeVO[]>(`${currBaseUrl}/query-menuTree`, {}, { showLoading: true }),
    success,
    fail
  )
}

export const getMenuDetail = async (
  id: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<any>(`${currBaseUrl}/get-by-id/${id}`, {}, { showLoading: true }),
    success,
    fail
  )
}

export const addMenu = async (params: any, success: RequestCallback, fail: RequestCallback) => {
  return handleJsonRequest(
    http.post<string>(`${currBaseUrl}/add-menu`, params, { showLoading: true }),
    success,
    fail
  )
}

export const updateMenu = async (
  id: string,
  params: any,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.put<string>(`${currBaseUrl}/modify-menu/${id}`, params, { showLoading: true }),
    success,
    fail
  )
}

export const deleteMenu = async (id: string, success: RequestCallback, fail: RequestCallback) => {
  return handleJsonRequest(
    http.delete<string>(`${currBaseUrl}/delete-menu/${id}`, {}, { showLoading: true }),
    success,
    fail
  )
}

export const MenuType = {
  INDEPENDENT: 0,
  AFFILIATED: 1
} as const

export const MenuModel = {
  TAB: 0,
  NEW_PAGE: 1
} as const
