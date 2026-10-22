// 움직임: 깜빡임(조각 바꾸기), 숨쉬기(가슴 뼈 크기 → 머리·마이크 손이 같이 오르내림), 손 흔들기(미리 휜 아래팔 그림 고르기).
function lerpKeys(keys, t, field) {
  if (t <= keys[0].time) return keys[0][field]
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1], b = keys[i]
    if (t <= b.time) { const u = (t - a.time) / (b.time - a.time || 1), s = 0.5 - Math.cos(u * Math.PI) / 2; return a[field] + (b[field] - a[field]) * s }
  }
  return keys[keys.length - 1][field]
}
export function samplePose(skel, now, { waveStart = null } = {}) {
  const A = skel.animations, pose = {}
  const br = A.breathe, tb = now % br.period
  pose.chest = { sy: lerpKeys(br.bones.chest.scale, tb, 'y') }
  let waving = false, waveAngle = 0
  if (waveStart != null) {
    const tw = now - waveStart, w = A.wave
    if (tw >= 0 && tw < w.period * (w.repeat || 1)) { waving = true; waveAngle = lerpKeys(w.angle, tw % w.period, 'value') }
  }
  const bk = A.blink.slots.eyes.attachment, t = now % A.blink.period
  let name = null
  for (const k of bk) if (t >= k.time) name = k.name
  return { pose, eyesClosed: name === 'eyes_closed', waving, waveAngle }
}
