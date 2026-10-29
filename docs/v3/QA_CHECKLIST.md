# 완성본 검수 체크리스트 (AI 티 없애기)

검수는 '완성본을 처음 보는 사람' 눈으로 한다. 점수 계산 전에 아래를 하나라도 못 넘으면 불합격.

## 보는 순서
1. 100% 전체(휴대폰 390px 화면) → 눈에 먼저 걸리는 것부터
2. 200% → 이음새·선
3. 400% → 가장자리·점·계단

## 이음새 하나씩 (옷 입음/안 입음 둘 다, 쉬는 자세·손 흔들기·깜빡임 모든 프레임)
목 · 양 어깨 · 양 팔꿈치(특히 restPose로 내린 마이크 팔) · 양 손목 · 허리 자름선 · 무릎 · 발목 · 머리와 몸이 만나는 곳

## 불합격 신호
- 레이어 이음새 경계선, 점선처럼 끊긴 바깥선, 직선으로 잘린 자국, 쐐기 모양 홈
- 갑자기 끊기는 선, 굵기가 바뀌는 선, 이중선
- 번짐, 흰 테두리(후광), 회색 테두리, 떨어진 점
- 질감·선명도가 부품마다 다른 곳(안쪽은 선명한데 바깥선만 흐림 등)
- 손가락·신발 같은 디테일 뭉개짐

## 과거에 놓친 것
- 2026-10: 마이크 팔을 restPose로 내린 뒤 위팔 바깥선이 점선·직선 자국으로 남음 → `tools/v3/fix_elbow.py`
- 2026-10: 720×1280 원화를 2배로 늘려 전체가 흐림 → `tools/v3/upscale_parts.py`(Real-ESRGAN anime_6B, 부품 2배 해상도)

## Round 2 additions
- 옷 소매 끝의 작은 닫힌 고리 조각(노란 쐐기) — 옷 입힌 상태 팔꿈치 400% 확인 (tools/v3/fix_fit.py)
- 머리 고리 속 흰 구멍(어깨) — 단색 셀 채색으로 메우기, 흐린 인페인트 금지 (tools/v3/fill_hair_holes.py)
- 변형 프레임(흔들기 팔) 가장자리의 회색·울퉁불퉁 선 — 모든 프레임 확인 (tools/v3/fix_wave_arm.py)
- 재생성 패치(B)는 라플라시안 선명도로 비교해 더 선명할 때만 적용

## Round 3 additions
- 머리-얼굴 사이 닫힌 틈의 흰 홈: 머리 그림자색으로 메우고, 선과 채움 사이 1~2px 밝은 띠가 남지 않게 (tools/v3/fill_head_gaps.py)
- 머리카락 끝의 고립된 어두운 점(60px 이하) 제거
- 파트 이미지 경계에 잘린 윤곽선(평평한 꺾임) 확인 — 흔들기 팔 0번 (tools/v3/fix_wave_arm0_edge.py)
- 목·손목·무릎·발목 400% 시트를 옷 입힘/안 입힘 × 기본/흔들기 모두 확인

## Round 4 — 업스케일 직후 외곽선 정리 (필수 단계)
- 파이프라인: ... → upscale_parts → **smooth_outlines** → **clean_white_tint** → fix_fit → fill_hair_holes → fix_wave_arm → fill_head_gaps
- smooth_outlines: 외곽 윤곽을 호 길이 가우시안(S=8, 다리 S=20)으로 스플라인처럼 매끈하게 다시 그리고, 몸 외곽선 굵기(9px@2x)로 통일. 실선 굵기 <6px 파츠(앞머리 가닥 등)는 원래 굵기 유지. 끝점(>3.5px 편차)은 보존. 실루엣 밖 반투명 헤일로 제거.
- clean_white_tint: 흰 속옷 안쪽 분홍 번짐 제거.
- fill_head_gaps 점 제거는 '진짜 고립점'만(≤30px, 변≤7, 9x9 주변에 어두운/투명 픽셀 없음). 머리 가닥 지우지 말 것.
- 검수: 다리 정강이·발목 400% 확인(흔들림 없는 한 줄), 옆머리 이중선 여부, 허리 바깥/안쪽 분홍 얼룩.

## Round 5 — 흔들기 파츠 동기화
- 파이프라인 끝: ... → clean_white_tint(허리 근처 skel y>1060만, 경계 페더) → fix_thigh_tick → **sync_wave_parts**(마지막)
- *_wave 파츠는 기본 파츠와 따로 처리하면 상자 밖이 몇 px씩 달라져 '상자 밖 바뀜' 실패가 난다. 흔들기 상자 밖은 기본 파츠에서 복사해 같은 처리 결과를 쓴다. 검사 기준·예외는 바꾸지 않는다.
- 다리는 라운드 3 백업(fx3)에서 smooth_outlines 한 번(S=20)만 적용.
- 푸시는 vitest와 check_frames(pass=true)가 모두 통과했을 때만 `&&`로 이어서 실행.

## Round 6 — 흔들기 머리 자국
- fix_wave_hair_streak(hair_back_wave): 팔이 비켜 간 자리의 옛 몸통 테두리 선이 옅은 흰·회색 줄로 남던 것을 주변 머리색으로 채움. sync_wave_parts 앞에 실행.
- 검수: 모든 흔들기 프레임(194장) 겨드랑이~머리 끝 영역 400% 시트(docs/v3/qa/v3-review9/sheet_*), 위=전, 아래=후.

## Round 7 (v3-review10)
- [x] 겨드랑이-머리 외곽선 흰 틈 메움 (fix_wave_hair_detail.py)
- [x] 평평한 채움에 머리결 3가닥 이어 그림
- [x] 외곽선 옆 점선(이중선) 제거, 남은 흰 획·회색 점 제거
- [x] 시트 20장 전/후 직접 육안 확인, 640프레임 check_frames 통과

## Round 8 (v3-review11)
- [x] 흔들기 상의 왼쪽 위 소매선 끝 두 갈래 → 한 줄로 가늘게(테이퍼), 옆 짧은 사선 조각 제거 (fix_sleeve_wave.py, basic/none 모두)
- [x] 겨드랑이 머리 시작점 흰 띠·구멍 메움, 아래 외곽선 가시 정리 (fix_wave_hair_detail 1d, fix_sleeve_wave)
- [x] 새 머리결: 직선·균일 폭 → 3차 곡선 + 위 굵고 아래로 가늘어지는 붓 터치 (hbw_r6 백업에서 복원 후 재실행)
- [x] 옆머리 묶음 근처 네모 회분홍 패치(옛 고리 구멍 단색 채움이 번진 것) → 주변 머리색으로 다시 채우고 이음선 제거 (fix_side_hair.py)
- [x] 머리카락 속 회색 스케치 선(body_upper 얼굴/귀 선이 앞머리 가장자리로 비침) 제거
- [x] 묶음 고리 외곽선 두께를 몸 외곽선 굵기로 맞춤, 알파 바늘구멍 메움
- 파이프라인: hbw_r6 복원 → fix_wave_hair_detail → fix_side_hair → fix_sleeve_wave → sync_wave_parts(마지막)

## Round 9 (v3-review12) — 남은 약점 4개 + 전체 라인 매끈화
- [x] wave 030 중앙 가는 가닥: 직선 지우고 주변 머리결 따라 휘는 베지어로 다시 그림 (`fix_r9.py`)
- [x] none 겨드랑이: 빨간 사선·머리 속 어두운 자국(구멍 포함) 제거, 경계 톤 부드럽게 (`fix_r9_armpit.py`, hair_back_wave만)
- [x] 오른쪽 리본 고리 그라데이션 끝 톤 경계 매끈화 + 매듭 끝 뭉툭함 정리 (`fix_r9_loops.py`)
- [x] 모든 파츠 라인 매끈화 (`smooth_lines.py`: 4배 초해상 SDF로 알파 외곽 + 잉크선 가장자리; 눈·얼굴 박스와 hair_front 톤 그라데이션 가닥은 보호)
- [x] hair_front 오른쪽 가닥 톤 끊김(이전 라운드 잔재) → HEAD 그라데이션 복원 (`fix_strand_blend.py`)
- [x] 파츠별 400% 전/후 시트: `docs/v3/qa/v3-review12/parts/*_400.png` (35장) 눈으로 확인
- [x] wave400 8장, 옆머리 비교, w390 전신(basic/none) 눈으로 확인
- [x] 640프레임 check_frames pass=True, vitest 통과 후에만 푸시
- 남은 약점: body_wave_arm_* 손가락 안쪽 선 가장자리 미세 요철, none 겨드랑이 아래 흐린 그림자 덩어리(빨간 선 제거 흔적)

## Round 10
- [x] body_wave_arm_* 손가락 안쪽 선: 요철·연분홍 테두리 제거 (fix_finger_edges.py, SDF 4x 슈퍼샘플)
- [x] none 겨드랑이 아래 흐린 분홍 그림자 → 주변 머리 톤으로 보정 (fix_r9_armpit.py)
- 증거: docs/v3/qa/v3-review13/

## Round 11 (9.4 지적 + 팔꿈치 최우선)
- [x] 겨드랑이(hair_back_wave): 계단 외곽선 SDF 매끈화, 흐린 가운데에 결선 3개+하이라이트 1개, 왼쪽 아래 짧은 세로 선 지움 — `qa/v3-review14/armpit_before_after_400.png`
- [x] wave 오른쪽 머리 갈래 갈색 점 제거 — `wave_split_dot_400.png`
- [x] wave 상의 왼쪽 아래 윗선 혹 제거 — `wave_top_bump_400.png`
- [x] 옆머리 고리 안쪽 선 옆 흰 점 제거(hair_back, hair_back_wave) — `side_loop_specks_400.png`
- [x] 팔꿈치: hand_r 아래 끝의 닫힌 외곽선과 윗팔 토막의 이중 외곽선을 하나의 팔꿈치 윤곽으로 합치고 사이 빈틈·얼룩을 피부로 채움. hand_r 캔버스 확장(x 383, width 192, height 487) — `elbow_*_100.png`, `elbow_*_400.png` (idle/wave, basic/none)
- [x] 390px 전신 — `phone390_fullbody.png`

## Round 12 — 팔꿈치 바깥선 스무딩 (hand_r)
- hand_r를 원본(ced7bc7 hand_r)에서 재생성: 윤곽 추출 → 가우시안 스플라인 스무딩(σ10→6, 팔꿈치 타원 영역만, 안쪽 접힘 제외) → 4× 래스터 SDF로 굵기 6.5px 일정 안티앨리어싱 선 (tools/v3/elbow_r12/fix_elbow2.py, bake3.py; 캔버스 384×974 고정, skeleton 변경 없음)
- 팔 왼쪽 삐친 머리카락 제거(hair_back, hair_back_wave; spike_r12.py), 선 안쪽 옛 선 자국 정리
- 주의: fix_r11 / elbow_r11 / spike_r12는 비멱등 — 재실행 금지(백업에서 복원 후에만)
- 전후 비교: docs/v3/qa/v3-review15/
- [ ] 400%에서 선 굵기 일정, 혹·계단·꺾임 없음 / 아래팔·윗팔 선 연결 / 회색 잔선 없음

## Round 13 — 윗팔/아래팔 축 정렬 (forearm_r pivot)
- 원인: forearm_r 회전 pivot (412,988)이 팔꿈치 관절이 아닌 전완 아래·왼쪽에 있어서, −34° 회전 시 전완이 바깥으로 밀림. 팔꿈치 높이에서 축 간 거리 56–60px(프레임), 두 축 교차점이 팔꿈치보다 80–100px 아래.
- 수정: 관절 J≈(498,816) 기준 회전과 같도록 restPose forearm_r에 이동 (x 111, y 19)을 더함. t=(I−R)(J−P). hand_r는 원본(372×930)으로 되돌려 r11/r12에서 덧그린 패치를 제거.
- body_upper/_wave: 아래팔 뒤에서 튀어나오던 옛 팔꿈치와 전완 꼬리를 지움 (part y>1560, x<270).
- hair_back/_wave: 머리카락 레이어에 남아 있던 밝은 피부색 덩어리(part 1450–1810, x 269–492)를 주변 머리 색으로 덮음.
- 결과: 팔꿈치 축 간 거리 약 10px, 교차점이 팔꿈치 위치와 일치. QA 이미지는 docs/v3/qa/v3-review16. 도구는 tools/v3/elbow_r13 (stub.py와 blob.py는 r13 백업에서 다시 만들어야 함. 멱등 아님).

## Round 14 — 허리 잘록 · 몸 옆 삐져나옴 · 발가락 (2026-10-29)
- 지적: "발가락 보인다", "허리가 잘록하게", "허리 옆으로 몸이 삐져나왔다".
- 원인 1(옆 삐져나옴): ① basic 옷 입었을 때 몸(body_*) 옆선이 치마 허리띠 옆으로 약 16px(그림 좌표) 바깥에 있었음.
  ② hair_back/_wave 안에 '흰 몸통 실루엣+외곽선'(옛 몸 옆선, 약 63만 px)이 구워져 있어서, 몸을 줄이면 허리 옆에 옛 옆선이 겹선으로 드러남.
- 원인 2(발가락): none 맨발 그림 자체에 발가락 선이 그려져 있었고, basic 에서는 맨발이 신발 옆으로 6–14px 나와 있었음.
- 수정(tools/v3/waist_r14, bak/ 원본에서 읽는 멱등 스크립트):
  - waist14.py: 옷과 몸을 함께 가로로만 잘록(최대 6.5%, y≈2050 중심 가우시안). 몸은 옷 옆선보다 3px 안쪽까지 한 번 더 줄임.
    발은 신발 중심 기준 가로 축소(신발 밖 살 0), 맨발 발가락 선은 주변 살색으로 채우고 넓게 흐려 줄무늬 없앰. 발 가장자리 축소 값을 위아래로 더 부드럽게(최소 25줄·가우시안 16).
  - hairside14.py: hair_back(_wave)에서 목 아래 흰 몸통 덩어리와 그 외곽선만 지움(머리 분홍에 붙은 선은 남김).
- 새 자동 검사: tools/v3/skin_outside_enc.py(몸=파랑/외곽선=어두운 파랑, 옷=빨강, 다른 층=초록으로 칠한 사이트 복사본) +
  tools/v3/check_skin_outside.py.
  - A: 옷 실루엣 밖, 옷에서 30px 안에 붙은 살(몸) 조각 → 0이어야 함(허리 양옆 특히).
  - B: 몸/옷 실루엣 바깥 4–40px 띠(몸통 높이)에 보이는 흰/살색 덩어리(머리 뒤 층의 옛 몸통) → 0이어야 함.
  - 몸통 띠 위끝은 몸 중심 열에서 옷이 시작되는 줄(흔들기 때 든 소매 때문에 얼굴이 띠에 들어가 생긴 오탐 27건을 없앰).
  - 검증: 9d5a7d6 원본은 A 5건(basic idle/wave 허리 옆), '몸만 줄이고 머리 뒤 층 그대로'는 B 4건(none idle/wave) → 수정 후 640프레임 0건. check_frames 640프레임 통과(fails 0).
  - check_frames.py 는 그대로(느슨하게 하지 않음).
- 이미 있던 것(이번에 안 고침): 윗옷 아랫단 선이 허리띠 위에서 두 군데 1–2px 계단처럼 끊김(9d5a7d6 에도 같음).
- QA 이미지: docs/v3/qa/v3-review17 (waist_left_400 / waist_right_400 / waist_full_100 / waist_full_400 / feet_100 / feet_400, 각 왼쪽=전, 오른쪽=후).
