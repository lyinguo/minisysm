import { expect, describe, it, beforeAll, afterAll } from 'vitest'
import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { withSetup } from '../test-apis-settings'
import { useHttp, HttpClient } from '@/plugins/http'
import type { PageDTO } from '@/apis/type'
import type { Article } from './type'

/** Real loopback transport checks; no external demo service or business database. */
describe('http', () => {
  let app: any
  let http: HttpClient
  let server: Server
  let previousBase: string | undefined
  const requests: Array<{ method: string; path: string; body: any }> = []
  const article: Article = { id:'1',title:'测试标题',keywords:'测试',summary:'测试摘要',content:'测试内容',date:'2026-11-16' }
  beforeAll(async () => {
    server = createServer((request, response) => {
      response.setHeader('Access-Control-Allow-Origin', '*')
      response.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
      response.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization')
      response.setHeader('Content-Type', 'application/json')
      response.setHeader('Connection', 'close')
      if (request.method === 'OPTIONS') { response.writeHead(204);response.end();return }
      let text = ''
      request.on('data', chunk => { text += chunk.toString() })
      request.on('end', () => {
        const path = request.url || '/'
        const body = text ? JSON.parse(text) : null
        requests.push({method:request.method || '',path,body})
        const url = new URL(path, 'http://localhost')
        if (url.pathname !== '/article' && url.pathname !== '/article/233') {response.writeHead(404);response.end('{}');return}
        const data = request.method === 'GET' ? {rows:[article],total:1,pageIndex:Number(url.searchParams.get('pageIndex')),pageSize:Number(url.searchParams.get('pageSize'))}
          : request.method === 'DELETE' ? {...article,id:'233'} : {...article,...body}
        response.end(JSON.stringify({code:10000,data}))
      })
    })
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
    app = withSetup(() => (http = useHttp()))[1]
    previousBase = http.getInstance().defaults.baseURL
    http.getInstance().defaults.baseURL = `http://127.0.0.1:${(server.address() as AddressInfo).port}`
  })
  afterAll(async () => {
    http.getInstance().defaults.baseURL = previousBase
    app.unmount()
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  })
  it('getSync', async () => {
    await http.get<PageDTO<Article>>('/article',{pageIndex:1,pageSize:2}).then(data => {
      expect(data.code).toBe(10000)
      expect(data.data?.rows?.[0]?.title).toBe(article.title)
    })
    expect(requests.at(-1)?.method).toBe('GET')
  })
  it('getAsync', async () => {
    const data = await http.get<PageDTO<Article>>('/article',{pageIndex:1,pageSize:2})
    expect(data.code).toBe(10000)
    expect(data.data?.rows?.[0]?.id).toBe('1')
    expect(requests.at(-1)?.path).toContain('pageSize=2')
  })
  it('post', async () => {
    const data = await http.post<Article>('/article',article)
    expect(data.code).toBe(10000)
    expect(data.data?.content).toBe(article.content)
    expect(requests.at(-1)).toMatchObject({method:'POST',path:'/article',body:article})
  })
  it('put', async () => {
    const data = await http.put<Article>('/article',{...article,title:'修改标题'})
    expect(data.code).toBe(10000)
    expect(data.data?.title).toBe('修改标题')
    expect(requests.at(-1)).toMatchObject({method:'PUT',path:'/article',body:{id:'1',title:'修改标题'}})
  })
  it('delete', async () => {
    const data = await http.delete<Article>('/article/233')
    expect(data.code).toBe(10000)
    expect(data.data?.id).toBe('233')
    expect(requests.at(-1)).toMatchObject({method:'DELETE',path:'/article/233'})
  })
})
