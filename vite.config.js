import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const here = dirname(fileURLToPath(import.meta.url))

function listFiles(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) out.push(...listFiles(p))
    else out.push(p)
  }
  return out
}

function sihaPwaPlugin() {
  return {
    name: 'siha-pwa',
    closeBundle() {
      const dist = join(here, 'dist')
      if (!existsSync(join(dist, 'sw.js'))) return

      const rels = listFiles(dist)
        .map((p) => relative(dist, p).split('\\').join('/'))
        .filter((r) => r !== 'sw.js' && !r.endsWith('.map') && !r.startsWith('v3-demo/') && !r.startsWith('assets/v3'))
        .sort()
      let sw = readFileSync(join(dist, 'sw.js'), 'utf8')
      // sw.js 본문이 바뀌어도(캐시 규칙 수정 등) 캐시 버전이 새로 나오게 본문도 지문에 넣는다.
      const fingerprint = rels.map((r) => `${r}:${statSync(join(dist, r)).size}`).join('|') + `|sw:${sw}`
      const version = `siha-stickerbook-v${createHash('sha256').update(fingerprint).digest('hex').slice(0, 10)}`
      const urls = ['./', ...rels.map((r) => `./${r}`)]

      sw = sw.replace("'__SIHA_CACHE_VERSION__'", JSON.stringify(version))
      sw = sw.replace("['__SIHA_PRECACHE__']", JSON.stringify(urls))
      writeFileSync(join(dist, 'sw.js'), sw)
      console.log(`[siha-pwa] ${version}  precache ${urls.length} urls`)
    },
  }
}

// GitHub Pages: https://dmlwjd85.github.io/siha-sticker-book/
export default defineConfig({
  plugins: [react(), sihaPwaPlugin()],
  base: '/siha-sticker-book/',
  server: { port: 5178, strictPort: true },
  // v3 데모는 따로 쪽(/siha-sticker-book/v3-demo/). 지금 앱(index.html)·저장 키는 그대로.
  build: { target: 'es2022', rollupOptions: { input: { main: join(here, 'index.html'), v3demo: join(here, 'v3-demo/index.html') }, output: { entryFileNames: (c) => (c.name === 'v3demo' ? 'assets/v3demo-[hash].js' : 'assets/[name]-[hash].js') } } },
})
