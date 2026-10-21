// v3 데모 앱: 지금 앱과 따로(자기 저장 키). 그림은 전부 public/v3-demo/ 의 생성 그림 조각.
import { worldTransforms, drawList, nearestBone, apply, invert } from './model.js'
import { samplePose } from './motion.js'
export const STORAGE_KEY = 'siha-v3-demo-v1'
const BASE = import.meta.env.BASE_URL + 'v3-demo/'
const cv = document.getElementById('c'), g = cv.getContext('2d')
const imgs = {}
const load = (p) => imgs[p] || (imgs[p] = new Promise((r) => { const i = new Image(); i.onload = () => r(i); i.src = BASE + p }))
function loadState() {
  try { const s = JSON.parse(localStorage.getItem(STORAGE_KEY)); if (s && s.v === 1) return s } catch { /* 없음 */ }
  return { v: 1, outfit: 'basic', accs: {} }
}
let state = loadState()
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
const skel = await (await fetch(BASE + 'skeleton.json')).json()
const PAD = skel.skeleton.stagePad || 0 // 무대 좌우 여백: 손을 흔들어도 손끝이 무대 안
cv.width = skel.skeleton.width + PAD * 2
const IM = {}
for (const s of Object.values(skel.skins[0].attachments)) for (const a of Object.values(s)) IM[a.path] = await load(a.path)
for (const a of skel.accessories) IM[a.path] = await load(a.path)
const ACC_SCALE = 0.32
export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
let waveStart = null, drag = null, world = {}
function accRect(a, st) {
  const W = world[st.bone], [x, y] = apply(W, st.x, st.y), w = a.width * ACC_SCALE * (st.size || 1), h = a.height * ACC_SCALE * (st.size || 1)
  const rot = Math.atan2(W[1], W[0])
  // 움직이는 동안에도 무대 안에: 돌아도 안 나가게 대각선 반만큼 안쪽으로 묶는다
  const r = Math.hypot(w, h) / 2
  return { x: clamp(x, r - PAD, cv.width - PAD - r), y: clamp(y, r, cv.height - r), w, h, rot }
}
function frame(ts) {
  const now = ts / 1000
  const { pose, eyesClosed, waving, waveUp } = samplePose(skel, now, { waveStart })
  if (!waving && waveStart != null && now - waveStart > 0) waveStart = null
  world = worldTransforms(skel, pose)
  g.clearRect(0, 0, cv.width, cv.height)
  for (const p of drawList(skel, { outfit: state.outfit, eyesClosed, waveUp })) {
    const m = world[p.bone]
    g.setTransform(m[0], m[1], m[2], m[3], m[4] + PAD, m[5])
    g.drawImage(IM[p.path], p.x, p.y, p.width, p.height)
  }
  for (const a of skel.accessories) {
    const st = state.accs[a.name]; if (!st) continue
    const r = accRect(a, st)
    g.setTransform(Math.cos(r.rot), Math.sin(r.rot), -Math.sin(r.rot), Math.cos(r.rot), r.x + PAD, r.y)
    g.drawImage(IM[a.path], -r.w / 2, -r.h / 2, r.w, r.h)
  }
  g.setTransform(1, 0, 0, 1, 0, 0)
  requestAnimationFrame(frame)
}
requestAnimationFrame(frame)
const toCanvas = (e) => { const b = cv.getBoundingClientRect(); return [((e.clientX - b.left) / b.width) * cv.width - PAD, ((e.clientY - b.top) / b.height) * cv.height] }
// 놓은 자리에서 가장 가까운 뼈에 붙인다(뼈 좌표로 저장 → 뼈가 움직이면 같이 움직임)
function attach(name, x, y) {
  const bone = nearestBone(skel, x, y)
  const [lx, ly] = apply(invert(world[bone]), x, y)
  state.accs[name] = { ...(state.accs[name] || {}), bone, x: lx, y: ly }
}
cv.addEventListener('pointerdown', (e) => {
  const [x, y] = toCanvas(e)
  for (const a of [...skel.accessories].reverse()) {
    const st = state.accs[a.name]; if (!st) continue
    const r = accRect(a, st)
    if (Math.abs(x - r.x) < r.w / 2 + 12 && Math.abs(y - r.y) < r.h / 2 + 12) { drag = a.name; cv.setPointerCapture(e.pointerId); return }
  }
})
cv.addEventListener('pointermove', (e) => { if (drag) { const [x, y] = toCanvas(e); attach(drag, x, y) } })
cv.addEventListener('pointerup', () => { if (drag) { drag = null; save() } })
const $ = (id) => document.getElementById(id)
function sync() {
  $('outfit').setAttribute('aria-pressed', String(state.outfit === 'basic'))
  for (const a of skel.accessories) $(a.name).setAttribute('aria-pressed', String(!!state.accs[a.name]))
}
$('outfit').onclick = () => { state.outfit = state.outfit === 'basic' ? null : 'basic'; save(); sync() }
$('wave').onclick = () => { waveStart = performance.now() / 1000 }
// 기본 자리: 앞머리 위(눈썹·눈을 가리지 않음). y≈55 가 머리 꼭대기, 눈썹은 y≈150
const DEFAULT = { acc_ribbon: [290, 78], acc_star: [446, 84] }
for (const a of skel.accessories) $(a.name).onclick = () => {
  if (state.accs[a.name]) delete state.accs[a.name]; else attach(a.name, ...DEFAULT[a.name])
  save(); sync()
}
$('reset').onclick = () => { state = { v: 1, outfit: 'basic', accs: {} }; save(); sync() }
sync()
window.__v3 = { skel, get state() { return state }, STORAGE_KEY, PAD, accBoxes: () => skel.accessories.filter((a) => state.accs[a.name]).map((a) => { const r = accRect(a, state.accs[a.name]); return { ...r, r: Math.hypot(r.w, r.h) / 2 } }) }
