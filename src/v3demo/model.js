// 뼈대 모델: skeleton.json 을 읽어 뼈 월드 변환을 계산한다(쉬는 자세 기준 회전/이동/크기).
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
    const local = mul(mat(1, 0, 0, 1, jx + (p.x || 0), jy + (p.y || 0)), mul(mat(cs, sn, -sn, cs), mul(mat(sx, 0, 0, sy), mat(1, 0, 0, 1, -jx, -jy))))
    out[b.name] = b.parent ? mul(out[b.parent], local) : local
  }
  return out
}
/** 지금 그릴 조각 목록(슬롯 순서). state: {outfit, eyesClosed, waving, waveAngle, prop} */
export function drawList(skel, state) {
  const skin = skel.skins[0].attachments
  const fit = skel.outfits[state.outfit] || null
  const wave = skel.animations.wave
  const list = []
  for (const s of skel.slots) {
    let name = s.attachment || null
    if (state.waving && wave.swap[s.name]) name = wave.swap[s.name]
    if (s.name === 'fit_lower' || s.name === 'fit_upper') name = fit ? (state.waving ? fit.wave[s.name] : fit[s.name]) : null
    if (s.name === 'eyes') name = state.eyesClosed ? 'eyes_closed' : null
    if (s.name === 'prop') name = state.prop || null
    if (s.name === 'wave_arm') {
      if (!state.waving) continue
      // 미리 휘어 둔 아래팔 그림 중 지금 각도에 가장 가까운 것
      let f = wave.frames[0]
      for (const k of wave.frames) if (Math.abs(k.angle - state.waveAngle) < Math.abs(f.angle - state.waveAngle)) f = k
      list.push({ slot: s.name, bone: s.bone, ...f.body })
      if (fit) list.push({ slot: s.name, bone: s.bone, ...f.basic })
      continue
    }
    const a = name && skin[s.name]?.[name]
    if (!a) continue
    if (s.name === 'prop') {
      // 소품: 손잡이 grip 지점을 뼈 자리(주먹 가운데)에 두고 rotation 만큼 기울임
      const w = a.width * a.scale, h = a.height * a.scale
      list.push({ slot: s.name, bone: s.bone, path: a.path, prop: true, rotation: a.rotation, x: -w / 2, y: -h * a.grip, width: w, height: h })
      continue
    }
    list.push({ slot: s.name, bone: s.bone, ...a })
  }
  return list
}
/** 점에서 가장 가까운 뼈(쉬는 자세 좌표) */
export function nearestBone(skel, x, y) {
  let best = null, bd = Infinity
  for (const b of skel.bones) {
    if (!b.parent || b.name === 'prop_r') continue
    const a = b.rest, kids = skel.bones.filter((k) => k.parent === b.name && k.name !== 'prop_r')
    const e = kids.length ? kids[0].rest : { x: a.x, y: a.y + (b.name === 'head' ? -400 : 0) }
    const dx = e.x - a.x, dy = e.y - a.y, L2 = dx * dx + dy * dy || 1
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / L2))
    const d = Math.hypot(x - a.x - t * dx, y - a.y - t * dy)
    if (d < bd) { bd = d; best = b.name }
  }
  return best
}
