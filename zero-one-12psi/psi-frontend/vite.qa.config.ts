import { mergeConfig, defineConfig } from 'vite'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import base from './vite.config'

const privateSession = fileURLToPath(new URL('../../qa/runtime/browser-session.json', import.meta.url))
const config = mergeConfig(base, defineConfig({
  server: {
    host: '127.0.0.1', port: 18030, strictPort: true, open: false,
    hmr: { host: '127.0.0.1', port: 18030 },
  },
  plugins: [{
    name: 'private-qa-session',
    configureServer(server) {
      server.middlewares.use('/api', (request, response, next) => {
        if (['/c1-systemparameters/', '/j7-sysargs/', '/store/', '/goods/', '/basic_information/', '/sale/', '/j3-purchase/', '/homepage/'].some(prefix => request.url?.startsWith(prefix))) { next(); return }
        response.statusCode = 503
        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        response.end(JSON.stringify({ code: 9998, message: '隔离验收环境尚未启动此业务服务' }))
      })
      server.middlewares.use('/qa-session', (_request, response) => {
        response.setHeader('Content-Type', 'application/json')
        response.setHeader('Cache-Control', 'no-store')
        response.end(readFileSync(privateSession, 'utf-8'))
      })
    }
  }]
}))
config.server!.proxy = {
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
