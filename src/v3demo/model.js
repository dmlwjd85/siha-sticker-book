// 뼈대 모델: skeleton.json 을 읽어 뼈 월드 변환을 계산한다(뼈 쉬는 자세 기준 회전/이동/크기).
export function mat(a = 1, b = 0, c = 0, d = 1, e = 0, f = 0) { return [a, b, c, d, e, f] }
export function mul(m, n) {
  return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]]
}
export function apply(m, x, y) { return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]] }
export function invert(m) {
  const det = m[0] * m[3] - m[1] * m[2]
  const a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det
  return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])]
}
/** pose: {bone: {rotate(deg), x, y, sx, sy}} → {bone: 월드 행렬(쉬는 자세 캔버스 좌표 → 지금 좌표)} */
export function worldTransforms(skel, pose = {}) {
  const out = {}
  for (const b of skel.bones) {
    const p = pose[b.name] || {}
    const { x: jx, y: jy } = b.rest
    const r = ((p.rotate || 0) * Math.PI) / 180
    const cs = Math.cos(r), sn = Math.sin(r)
    const sx = p.sx ?? 1, sy = p.sy ?? 1
    // 관절 기준: T(j + 이동) · R · S · T(-j)
    let local = mul(mat(1, 0, 0, 1, jx + (p.x || 0), jy + (p.y || 0)), mul(mat(cs, sn, -sn, cs), mul(mat(sx, 0, 0, sy), mat(1, 0, 0, 1, -jx, -jy))))
    out[b.name] = b.parent ? mul(out[b.parent], local) : local
  }
  return out
}
/** 지금 그릴 조각 목록(슬롯 순서) */
export function drawList(skel, state) {
  const skin = skel.skins[0].attachments
  const fit = skel.outfits[state.outfit] || null
  const list = []
  const swap = skel.animations?.wave?.swap
  for (const s of skel.slots) {
    // 손 흔들기 자세: 내린 팔 조각을 숨기고 든 팔(소매 포함 한 장)을 보인다
    if (swap && state.waveUp && swap.hide.includes(s.name)) continue
    if (swap && !state.waveUp && swap.show.includes(s.name)) continue
    let name = s.attachment || null
    if (s.name === 'arm_up_r' && fit && fit.arm_up_r) name = fit.arm_up_r
    if (s.name === 'eyes') name = state.eyesClosed ? 'eyes_closed' : null
    if (fit && fit[s.name]) name = fit[s.name]
    if (s.name === 'top' || s.name === 'bottom' || s.name.startsWith('socks') || s.name.startsWith('shoes') || s.name.startsWith('sleeve')) name = fit ? fit[s.name] : null
    if (name && skin[s.name]?.[name]) list.push({ slot: s.name, bone: s.bone, ...skin[s.name][name] })
  }
  return list
}
/** 점에서 가장 가까운 뼈(쉬는 자세 좌표) */
export function nearestBone(skel, x, y) {
  let best = null, bd = Infinity
  const R = Object.fromEntries(skel.bones.map((b) => [b.name, b]))
  for (const b of skel.bones) {
    if (!b.parent) continue
    const a = b.rest, kids = skel.bones.filter((k) => k.parent === b.name)
    const e = kids.length ? kids[0].rest : { x: a.x, y: a.y + (b.name === 'head' ? -200 : 0) }
    const dx = e.x - a.x, dy = e.y - a.y, L2 = dx * dx + dy * dy || 1
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / L2))
    const d = Math.hypot(x - a.x - t * dx, y - a.y - t * dy)
    if (d < bd) { bd = d; best = b.name }
  }
  void R
  return best
}
