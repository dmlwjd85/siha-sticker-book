// v4 B안 데모: public/v4b-demo/ 의 부위 레이어(2배)를 뼈대로 그림. 저장 키는 따로(siha-v4b-demo-v1).
import { samplePose, worldTransforms, STORAGE_KEY, toggleItem, visibleSlots } from './rig.js'
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
const ITEM_IDS = new Set((skel.items || []).map((i) => i.id))
function loadWorn() { try { const o = JSON.parse(localStorage.getItem(STORAGE_KEY)); return Array.isArray(o?.worn) ? o.worn.filter((w) => ITEM_IDS.has(w)) : [] } catch { return [] } }
let worn = loadWorn()
const saveWorn = () => localStorage.setItem(STORAGE_KEY, JSON.stringify({ v: 1, worn }))
const itemsBar = document.getElementById('items')
function syncButtons() { if (itemsBar) for (const b of itemsBar.querySelectorAll('button')) b.setAttribute('aria-pressed', String(worn.includes(b.dataset.id))) }
if (itemsBar) for (const it of skel.items || []) {
  const b = document.createElement('button'); b.dataset.id = it.id; b.textContent = it.label
  b.onclick = () => { worn = toggleItem(skel, worn, it.id); saveWorn(); syncButtons() }
  itemsBar.appendChild(b)
}
syncButtons()
function draw(now) {
  const { pose, waving } = samplePose(skel, now, waveStart)
  if (!waving && waveStart != null && now - waveStart > 0) waveStart = null
  const W = worldTransforms(skel, pose)
  g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height)
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'
  for (const s of visibleSlots(skel, worn)) {
    const m = W[s.bone]
    g.setTransform(m[0] * K, m[1] * K, m[2] * K, m[3] * K, (m[4] + PAD) * K, m[5] * K)
    g.drawImage(IM[s.name], s.x, s.y, s.width, s.height)
  }
  g.setTransform(1, 0, 0, 1, 0, 0)
}
function frame(ts) { if (!FIX) draw(ts / 1000); requestAnimationFrame(frame) }
requestAnimationFrame(frame)
document.getElementById('wave').onclick = () => { waveStart = performance.now() / 1000 }
document.getElementById('reset').onclick = () => { waveStart = null; worn = []; saveWorn(); syncButtons() }
// 검사용(tools/v3/check_frames.mjs 와 같은 모양): outfit 'basic' = 원피스+요술봉+티아라, null = 아이템 없음, 배열 = 그 아이템들, 생략 = 지금 입은 것
const OUTFIT = { basic: ['dress', 'wand', 'tiara'] }
window.__v3 = window.__v4b = { skel, renderAt(now, ws = null, outfit) { FIX = true; waveStart = ws; if (outfit !== undefined) worn = outfit === null ? [] : Array.isArray(outfit) ? outfit : OUTFIT[outfit] || []; draw(now); return cv.toDataURL('image/png') }, get worn() { return [...worn] }, live() { FIX = null }, get K() { return K }, STORAGE_KEY, PAD }
