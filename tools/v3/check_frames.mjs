// 모든 동작의 모든 프레임 캡처(손 흔들기·깜빡임·숨쉬기 × 옷 입음/안 입음). 분석은 check_frames.py 가 한다.
// 사용: 저장소에서 npm i --no-save playwright 한 번, vite preview 를 띄운 뒤 node tools/v3/check_frames.mjs <URL> <출력폴더>
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const url = process.argv[2] || 'http://localhost:4179/siha-sticker-book/v3-demo/'
const out = process.argv[3] || '/tmp/frames'
mkdirSync(out, { recursive: true })
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 })
await p.goto(url); await p.waitForFunction(() => window.__v3); await p.waitForTimeout(500)
const FPS = 30, list = []
const save = async (name, now, ws, outfit) => {
  const d = await p.evaluate(([n, w, o]) => window.__v3.renderAt(n, w, o), [now, ws, outfit])
  writeFileSync(`${out}/${name}.png`, Buffer.from(d.split(',')[1], 'base64')); list.push({ name, now, ws, outfit })
}
for (const outfit of ['basic', null]) {
  const tag = outfit || 'none'
  const W = await p.evaluate(() => window.__v3.skel.animations.wave), dur = W.period * (W.repeat || 1)
  for (let i = 0; i <= Math.round(dur * FPS); i++) {           // 손 흔들기 + 같은 시각의 기준(흔들기 없음)
    const t = 10 + i / FPS
    await save(`${tag}_wave_${String(i).padStart(3, '0')}`, t, 10, outfit)
    await save(`${tag}_ref_${String(i).padStart(3, '0')}`, t, null, outfit)
  }
  for (let i = 0; i < Math.round(4.2 * FPS); i++) await save(`${tag}_idle_${String(i).padStart(3, '0')}`, 42 + i / FPS, null, outfit) // 깜빡임·숨쉬기 한 바퀴
}
writeFileSync(`${out}/frames.json`, JSON.stringify(list))
console.log('frames', list.length); await b.close()
