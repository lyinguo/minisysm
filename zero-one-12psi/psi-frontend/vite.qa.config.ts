import { mergeConfig, defineConfig } from 'vite'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import base from './vite.config'

const privateSession = fileURLToPath(new URL('../../qa/runtime/browser-session.json', import.meta.url))
const privateState = fileURLToPath(new URL('../../qa/.state.json', import.meta.url))
const localRequest = (request: any) => ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(request.socket.remoteAddress)
const config = mergeConfig(base, defineConfig({
  server: {
    host: '127.0.0.1', port: 18030, strictPort: true, open: false,
    hmr: { host: '127.0.0.1', port: 18030 },
  },
  plugins: [{
    name: 'private-qa-session',
    configureServer(server) {
      server.middlewares.use('/qa-browser-login', (request, response) => {
        if (!localRequest(request)) { response.statusCode=403;response.end();return }
        const state=JSON.parse(readFileSync(privateState,'utf-8').replace(/^\uFEFF/,''))
        if (!/^psi_qa_[0-9a-f]{12}$/.test(state.database)) {response.statusCode=503;response.end();return}
        response.setHeader('Content-Type','text/html; charset=utf-8');response.setHeader('Cache-Control','no-store')
        response.end(`<!doctype html><meta charset="utf-8"><title>隔离业务验收会话</title><h1>隔离业务验收会话</h1><p>仅使用已由真实OAuth签发的新建QA账号会话，业务数据写入隔离环境。</p><button id="login">进入采购订单验收</button><p id="error"></p><script>document.querySelector('#login').onclick=async()=>{try{const response=await fetch('/qa-session');if(!response.ok)throw Error('隔离会话不可用');const session=await response.json();if(!session.token)throw Error('请先准备QA会话');localStorage.setItem('token',session.token);localStorage.removeItem('refreshToken');location.href='/purchase-booking-report'}catch(error){document.querySelector('#error').textContent=error.message}}</script>`)
      })
      server.middlewares.use('/api', async (request, response, next) => {
        // These two read-only shell endpoints validate the signed token against the real QA user service.
        // Menus are deliberately empty: this harness does not claim menu-service acceptance.
        if (request.url?.startsWith('/login/current-user') || request.url?.startsWith('/login/get-menus')) {
          response.setHeader('Content-Type','application/json; charset=utf-8');response.setHeader('Cache-Control','no-store')
          try {
            if(!localRequest(request) || request.method!=='GET')throw Error('Local GET only')
            const state=JSON.parse(readFileSync(privateState,'utf-8').replace(/^\uFEFF/,''))
            if(!/^psi_qa_[0-9a-f]{12}$/.test(state.database) || state.c1_port!==18091)throw Error('Invalid QA binding')
            const authorization=request.headers.authorization || ''
            if(!authorization.startsWith('Bearer '))throw Error('Missing token')
            const claims=JSON.parse(Buffer.from(authorization.slice(7).split('.')[1] || '', 'base64url').toString('utf-8'))
            if(typeof claims.id!=='string' || !claims.id)throw Error('Invalid actor')
            const checked=await fetch('http://127.0.0.1:18091/user/query-one?id='+encodeURIComponent(claims.id),{headers:{Authorization:authorization}})
            const user=await checked.json() as any
            if(!checked.ok || user.code!==10000 || user.data?.id!==claims.id)throw Error('QA account validation failed')
            response.end(JSON.stringify({code:10000,data:request.url.startsWith('/login/get-menus')?[]:{id:user.data.id,username:user.data.name || user.data.user,roles:user.data.role==='0'?['ROLE_ADMIN']:[]}}))
          } catch {response.statusCode=401;response.end(JSON.stringify({code:401,message:'隔离验收会话无效，请重新准备QA会话'}))}
          return
        }
        if (request.url === '/fund/receipt' || request.url?.startsWith('/otherin') || request.url?.startsWith('/otherout') || request.url?.startsWith('/transfer/report-documents/') || ['/j2-store/', '/c1-systemparameters/', '/j7-sysargs/', '/store/', '/goods/', '/basic_information/', '/sale/', '/j3-purchase/', '/homepage/', '/payment-order/', '/fund/receipt/'].some(prefix => request.url?.startsWith(prefix))) { next(); return }
        response.statusCode = 503
        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        response.end(JSON.stringify({ code: 9998, message: '隔离验收环境尚未启动此业务服务' }))
      })
      server.middlewares.use('/qa-session', (_request, response) => {
        if(!localRequest(_request)){response.statusCode=403;response.end();return}
        response.setHeader('Content-Type', 'application/json')
        response.setHeader('Cache-Control', 'no-store')
        response.end(readFileSync(privateSession, 'utf-8'))
      })
    }
  }]
}))
config.server!.proxy = {
  '/api/j2-store': { target: 'http://127.0.0.1:18001', rewrite: path => path.replace('/api', '') },
  '/api/otherout': { target: 'http://127.0.0.1:18001', rewrite: path => path.replace('/api', '/j2-store') },
  '/api/otherin': { target: 'http://127.0.0.1:18020', rewrite: path => path.replace('/api', '') },
  '/api/transfer/report-documents': { target: 'http://127.0.0.1:18020', rewrite: path => path.replace('/api', '') },
  '/api/fund/receipt': { target: 'http://127.0.0.1:18026', rewrite: path => path.replace('/api', '') },
  '/api/payment-order': { target: 'http://127.0.0.1:18024', rewrite: path => path.replace('/api', '') },
  '/api/homepage': { target: 'http://127.0.0.1:18025', rewrite: path => path.replace('/api', '') },
  '/api/c1-systemparameters': { target: 'http://127.0.0.1:18091', rewrite: path => path.replace('/api/c1-systemparameters', '') },
  '/api/j7-sysargs': { target: 'http://127.0.0.1:18007', rewrite: path => path.replace('/api/j7-sysargs', '') },
  '/api/store': { target: 'http://127.0.0.1:18020', rewrite: path => path.replace('/api/store', '') },
  '/api/sale': { target: 'http://127.0.0.1:18022', rewrite: path => path.replace('/api', '') },
  '/api/j3-purchase': { target: 'http://127.0.0.1:18023', rewrite: path => path.replace('/api/j3-purchase', '') },
  '/api/goods': { target: 'http://127.0.0.1:18021', rewrite: path => path.replace('/api', '') },
  '/api/basic_information': { target: 'http://127.0.0.1:18021', rewrite: path => path.replace('/api', '') }
}
export default config
