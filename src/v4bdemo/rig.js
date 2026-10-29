// v4 B안 데모 뼈대: 부위 레이어(관절 24px 겹침)를 뼈에 붙여 그린다. 지금 앱·v3 데모와 따로.
export const STORAGE_KEY = 'siha-v4b-demo-v1'
const ease = (u) => 0.5 - Math.cos(u * Math.PI) / 2
export function lerpKeys(keys, t) {
  if (t <= keys[0][0]) return keys[0][1]
  for (let i = 1; i < keys.length; i++) {
    const [ta, va] = keys[i - 1], [tb, vb] = keys[i]
    if (t <= tb) return va + (vb - va) * ease((t - ta) / (tb - ta || 1))
  }
  return keys[keys.length - 1][1]
}
/** now(초), waveStart(초|null) → 뼈별 {rotate(도), y} */
export function samplePose(skel, now, waveStart = null) {
  const A = skel.animations, pose = {}
  pose.chest = { rotate: 0, y: lerpKeys(A.breathe.y, now % A.breathe.period) }
  let waving = false
  if (waveStart != null) {
    const w = A.wave, tw = now - waveStart
    if (tw >= 0 && tw < w.period * (w.repeat || 1)) { waving = true; pose[w.bone] = { rotate: lerpKeys(w.angle, tw % w.period), y: 0 } }
  }
  return { pose, waving }
}
const mul = (m, n) => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3], m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]]
export function worldTransforms(skel, pose) {
  const out = {}
  for (const b of skel.bones) {
    const p = pose[b.name] || {}, r = ((p.rotate || 0) * Math.PI) / 180, c = Math.cos(r), s = Math.sin(r), { x, y } = b.rest
    const local = mul([1, 0, 0, 1, x, y + (p.y || 0)], mul([c, s, -s, c, 0, 0], [1, 0, 0, 1, -x, -y]))
    out[b.name] = b.parent ? mul(out[b.parent], local) : local
  }
  return out
}
