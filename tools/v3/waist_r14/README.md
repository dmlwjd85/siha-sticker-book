# Round 14 (2026-10-29) 허리 잘록 · 몸 옆 삐져나옴 · 발가락

원본(9d5a7d6 의 parts)을 bak/ 에 두고 읽으므로 몇 번 돌려도 결과가 같다(멱등). 경로는 작업 상자 기준.

1. `waist14.py` — 옷(basic_*)과 몸(body_*)을 함께 가로로만 잘록하게(중심 x=1434, y=2050, 폭 150, 6.5%).
   몸은 한 번 더 줄여 옷 옆선보다 3px 안쪽. 발: body_lower 발을 신발 중심 기준 가로 축소(신발 밖 살 0),
   맨발 발가락 선은 주변 살색으로 채운 뒤 넓게 흐려 줄무늬 없앰.
2. `hairside14.py` — hair_back(_wave) 안에 구워져 있던 '흰 몸통 실루엣 + 외곽선'(옛 몸 옆선)을 지움.
   몸을 줄이자 이것이 허리 옆으로 삐져나와 보였던 원인.
3. 검사: `tools/v3/skin_outside_enc.py dist /tmp/encroot` → `python3 -m http.server 4181 -d /tmp/encroot`
   → `node tools/v3/check_frames.mjs http://localhost:4181/siha-sticker-book/v3-demo/ /tmp/sk`
   → `python3 tools/v3/check_skin_outside.py /tmp/sk` (0건이어야 통과).
