// v4 B안 데모: public/v4b-demo/ 의 부위 레이어(2배)를 뼈대로 그림. 저장 키는 따로(siha-v4b-demo-v1).
import { samplePose, worldTransforms, STORAGE_KEY } from './rig.js'
const BASE = import.meta.env.BASE_URL + 'v4b-demo/'
const cv = document.getElementById('c'), g = cv.getContext('2d')
const skel = await (await fetch(BASE + 'skeleton.json')).json()
const PAD = skel.skeleton.stagePad, SW = skel.skeleton.width + PAD * 2, SH = skel.skeleton.height
let K = 1
function fitCanvas() { const b = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1; const w = Math.min(SW, Math.round(b.width * dpr)) || SW; K = w / SW; cv.width = w; cv.height = Math.round(SH * K) }
fitCanvas(); addEventListener('resize', fitCanvas)
const IM = {}
await Promise.all(skel.slots.map((s) => new Promise((r) => { const i = new Image(); i.onload = () => { IM[s.name] = i; r() }; i.src = BASE + s.path })))
let waveStart = null, FIX = null
function draw(now) {
  const { pose, waving } = samplePose(skel, now, waveStart)
  if (!waving && waveStart != null && now - waveStart > 0) waveStart = null
  const W = worldTransforms(skel, pose)
  g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height)
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'
  for (const s of skel.slots) {
    const m = W[s.bone]
    g.setTransform(m[0] * K, m[1] * K, m[2] * K, m[3] * K, (m[4] + PAD) * K, m[5] * K)
    g.drawImage(IM[s.name], s.x, s.y, s.width, s.height)
  }
  g.setTransform(1, 0, 0, 1, 0, 0)
}
function frame(ts) { if (!FIX) draw(ts / 1000); requestAnimationFrame(frame) }
requestAnimationFrame(frame)
document.getElementById('wave').onclick = () => { waveStart = performance.now() / 1000 }
document.getElementById('reset').onclick = () => { waveStart = null; localStorage.setItem(STORAGE_KEY, JSON.stringify({ v: 1 })) }
// 검사용(tools/v3/check_frames.mjs 와 같은 모양): outfit 은 이 데모에 없음(레오타드가 몸 그림에 포함)
window.__v3 = window.__v4b = { skel, renderAt(now, ws = null) { FIX = true; waveStart = ws; draw(now); return cv.toDataURL('image/png') }, live() { FIX = null }, get K() { return K }, STORAGE_KEY, PAD }
