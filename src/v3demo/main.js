// v3 데모 앱: 지금 앱과 따로(자기 저장 키). 그림은 전부 public/v3-demo/ 의 생성 그림 조각(2배 고해상도).
// 기본 자세: 한 손은 마이크를 쥐고(소품 슬롯 prop_r), 다른 손은 아래로 가볍게 쥠. 흔들기는 그 손을 들어 흔든다.
import { worldTransforms, drawList, nearestBone, apply, invert, mul } from './model.js'
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
const SW = skel.skeleton.width + PAD * 2, SH = skel.skeleton.height // 무대 좌표(그림 원본 크기)
// 선명하게: 캔버스 실제 픽셀 = 화면 크기 × 기기 픽셀비(최대 원본 크기). 그 위에 무대 좌표를 축소해서 그림
let K = 1
function fitCanvas() {
  const b = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1
  const w = Math.min(SW * 2, Math.round(b.width * dpr)) || SW   // 부품 그림은 무대 좌표의 2배 해상도
  K = w / SW; cv.width = w; cv.height = Math.round(SH * K)
}
fitCanvas(); addEventListener('resize', fitCanvas)
const IM = {}
for (const s of Object.values(skel.skins[0].attachments)) for (const a of Object.values(s)) IM[a.path] = await load(a.path)
for (const f of skel.animations.wave.frames) for (const a of [f.body, f.basic]) IM[a.path] = await load(a.path)
for (const a of skel.accessories) IM[a.path] = await load(a.path)
const ACC_SCALE = 0.32
export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
let waveStart = null, drag = null, world = {}
function accRect(a, st) {
  const W = world[st.bone], [x, y] = apply(W, st.x, st.y), w = a.width * ACC_SCALE * (st.size || 1), h = a.height * ACC_SCALE * (st.size || 1)
  const rot = Math.atan2(W[1], W[0])
  // 움직이는 동안에도 무대 안에: 돌아도 안 나가게 대각선 반만큼 안쪽으로 묶는다
  const r = Math.hypot(w, h) / 2
  return { x: clamp(x, r - PAD, SW - PAD - r), y: clamp(y, r, SH - r), w, h, rot }
}
let FIX = null // 검사용: 시간을 고정해서 한 프레임씩 그림(tools/v3/check_frames.mjs)
function frame(ts) {
  if (!FIX) draw(ts / 1000)
  requestAnimationFrame(frame)
}
function draw(now) {
  const { pose, eyesClosed, waving, waveAngle } = samplePose(skel, now, { waveStart })
  if (!waving && waveStart != null && now - waveStart > 0) waveStart = null
  world = worldTransforms(skel, pose)
  g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cv.width, cv.height)
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'
  for (const p of drawList(skel, { outfit: state.outfit, eyesClosed, waving, waveAngle, prop: state.prop === false ? null : 'mic' })) {
    let m = world[p.bone]
    if (p.prop) { const b = skel.bones.find((x) => x.name === p.bone).rest, r = (p.rotation * Math.PI) / 180; m = mul(m, [Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), b.x, b.y]) }
    g.setTransform(m[0] * K, m[1] * K, m[2] * K, m[3] * K, (m[4] + PAD) * K, m[5] * K)
    g.drawImage(IM[p.path], p.x, p.y, p.width, p.height)
  }
  for (const a of skel.accessories) {
    const st = state.accs[a.name]; if (!st) continue
    const r = accRect(a, st)
    g.setTransform(Math.cos(r.rot) * K, Math.sin(r.rot) * K, -Math.sin(r.rot) * K, Math.cos(r.rot) * K, (r.x + PAD) * K, r.y * K)
    g.drawImage(IM[a.path], -r.w / 2, -r.h / 2, r.w, r.h)
  }
  g.setTransform(1, 0, 0, 1, 0, 0)
}
requestAnimationFrame(frame)
const toCanvas = (e) => { const b = cv.getBoundingClientRect(); return [((e.clientX - b.left) / b.width) * SW - PAD, ((e.clientY - b.top) / b.height) * SH] }
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
  $('mic').setAttribute('aria-pressed', String(state.prop !== false))
  for (const a of skel.accessories) $(a.name).setAttribute('aria-pressed', String(!!state.accs[a.name]))
}
$('outfit').onclick = () => { state.outfit = state.outfit === 'basic' ? null : 'basic'; save(); sync() }
$('mic').onclick = () => { state.prop = state.prop === false ? 'mic' : false; save(); sync() }
$('wave').onclick = () => { waveStart = performance.now() / 1000 }
// 기본 자리: 앞머리 위(눈썹·눈을 가리지 않음). 2배 좌표: y≈125 가 머리 꼭대기, 눈썹은 y≈330
const DEFAULT = { acc_ribbon: [590, 170], acc_star: [880, 180] }
for (const a of skel.accessories) $(a.name).onclick = () => {
  if (state.accs[a.name]) delete state.accs[a.name]; else attach(a.name, ...DEFAULT[a.name])
  save(); sync()
}
$('reset').onclick = () => { state = { v: 1, outfit: 'basic', accs: {} }; save(); sync() }
sync()
window.__v3 = { skel, renderAt(now, ws = null, outfit) { FIX = true; waveStart = ws; if (outfit !== undefined) state.outfit = outfit; draw(now); return cv.toDataURL('image/png') }, live() { FIX = null }, get K() { return K }, get state() { return state }, STORAGE_KEY, PAD, accBoxes: () => skel.accessories.filter((a) => state.accs[a.name]).map((a) => { const r = accRect(a, state.accs[a.name]); return { ...r, r: Math.hypot(r.w, r.h) / 2 } }) }
