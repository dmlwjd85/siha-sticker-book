import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { samplePose, worldTransforms, STORAGE_KEY, toggleItem, visibleSlots } from './rig.js'
const skel = JSON.parse(readFileSync(new URL('../../public/v4b-demo/skeleton.json', import.meta.url)))
describe('v4b rig', () => {
  it('저장 키가 v3·지금 앱과 다르다', () => { expect(STORAGE_KEY).toBe('siha-v4b-demo-v1') })
  it('모든 슬롯 뼈가 있고 관절은 24px 이상 겹친다', () => {
    const names = new Set(skel.bones.map((b) => b.name))
    for (const s of skel.slots) expect(names.has(s.bone)).toBe(true)
    expect(skel.skeleton.jointOverlap).toBeGreaterThanOrEqual(24)
  })
  it('쉬는 자세는 단위 행렬, 흔들 때 어깨 관절점은 제자리', () => {
    const W0 = worldTransforms(skel, samplePose(skel, 0).pose)
    expect(W0.root).toEqual([1, 0, 0, 1, 0, 0])
    const wb = skel.animations.wave.bone, j = skel.bones.find((b) => b.name === wb).rest
    const { pose, waving } = samplePose(skel, 10.4, 10)
    expect(waving).toBe(true)
    pose.chest = { y: 0 }
    const m = worldTransforms(skel, pose)[wb]
    expect(m[0] * j.x + m[2] * j.y + m[4]).toBeCloseTo(j.x, 6)
    expect(m[1] * j.x + m[3] * j.y + m[5]).toBeCloseTo(j.y, 6)
  })
  it('아이템 입기/벗기: 원피스는 상의·치마와 바꿔 입고, 소품은 같이 든다', () => {
    let w = toggleItem(skel, [], 'top'); w = toggleItem(skel, w, 'skirt'); w = toggleItem(skel, w, 'wand')
    expect(w).toEqual(['top', 'skirt', 'wand'])
    w = toggleItem(skel, w, 'dress'); expect(w.sort()).toEqual(['dress', 'wand'])
    w = toggleItem(skel, w, 'dress'); expect(w).toEqual(['wand'])
  })
  it('아이템 슬롯은 입었을 때만 그리고, 소매는 흔드는 팔 뼈에 붙는다', () => {
    const base = visibleSlots(skel, []); expect(base.some((s) => s.item)).toBe(false)
    const d = visibleSlots(skel, ['dress']).filter((s) => s.item === 'dress')
    expect(d.find((s) => s.name.endsWith('sleeve_L')).bone).toBe(skel.animations.wave.bone)
    const ids = new Set(skel.items.map((i) => i.id)); for (const s of skel.slots) if (s.item) expect(ids.has(s.item)).toBe(true)
    expect(skel.slots.find((s) => s.item === 'wand').bone).toBe('hand_R')
    expect(skel.slots.find((s) => s.item === 'tiara').bone).toBe('head')
  })
})
