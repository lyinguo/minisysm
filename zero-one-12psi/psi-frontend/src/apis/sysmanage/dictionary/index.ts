/*
 * @Description: 系统配置-字典管理相关接口
 */
import { useHttp, type RequestCallback } from '@/plugins/http'
import type { PageDTO } from '@/components/mytable/type'
import { handleJsonRequest } from '@/apis/utils/jsonResponse'
import type {
  DictPageRequest,
  DictNameItem,
  DictDetailDTO,
  TypePageRequest,
  DictionTypeDTO,
  DictionaryTypeItem
} from './type'

const currBaseUrl = '/j1-sysc/dictionary-manager'
const http = useHttp()

/**
 * 字典
 */

export const getDictionaryList = async (
  params: DictPageRequest,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<PageDTO<any>>(`${currBaseUrl}/dict-queryList`, params, { showLoading: true }),
    success,
    fail
  )
}

export const getDictionaryNames = async (
  typeId: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<DictNameItem[]>(`${currBaseUrl}/dict-getNames`, { typeId }, { showLoading: true }),
    success,
    fail
  )
}

export const addDictionary = async (
  params: DictDetailDTO,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(http.post<string>(currBaseUrl, params, { showLoading: true }), success, fail)
}

export const updateDictionary = async (
  params: DictDetailDTO,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(http.put<string>(currBaseUrl, params, { showLoading: true }), success, fail)
}

export const deleteDictionary = async (
  dictId: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.delete<string>(`${currBaseUrl}/${dictId}`, {}, { showLoading: true }),
    success,
    fail
  )
}

/**
 * 字典类型
 */

export const getDictionaryTypeList = async (
  params: TypePageRequest,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<PageDTO<DictionTypeDTO>>(`${currBaseUrl}/dict-queryList-type`, params, {
      showLoading: true
    }),
    success,
    fail
  )
}

export const getDictionaryTypeNames = async (success: RequestCallback, fail: RequestCallback) => {
  return handleJsonRequest(
    http.get<DictionaryTypeItem[]>(`${currBaseUrl}/dict-getNames-type`, {}, { showLoading: true }),
    success,
    fail
  )
}

export const addDictionaryType = async (
  params: DictionTypeDTO,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.post<string>(`${currBaseUrl}/add-dict-type`, params, { showLoading: true }),
    success,
    fail
  )
}

export const updateDictionaryType = async (
  id: string,
  params: DictionTypeDTO,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.put<string>(`${currBaseUrl}/${id}`, params, { showLoading: true }),
    success,
    fail
  )
}

export const deleteDictionaryType = async (
  id: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.delete<string>(`${currBaseUrl}/remove-dict-type/${id}`, {}, { showLoading: true }),
    success,
    fail
  )
}
