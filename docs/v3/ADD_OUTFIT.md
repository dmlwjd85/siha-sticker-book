# 새 옷 넣는 법 (v3 뼈대)

1. **그림 만들기**: `docs/v3/PROMPTS.md` 의 "옷" 틀 + 참고 이미지 `tools/v3/raw/canon.jpg` 로 GenerateImage. 결과를 `tools/v3/raw/` 에 아무 이름으로 저장(원본은 고치지 않는다).
2. **조각 내기** (파일 이름 바꾸기 없음, 인자나 설정으로):
   - `python3 tools/v3/build_v3.py tools/v3/raw <out> --outfit basic=outfit.jpg --outfit summer=summer_dress.jpg`
   - 또는 `--config outfits.json` (`{"outfits": {"basic": "outfit.jpg", "summer": "summer_dress.jpg"}}`)
   - 아무것도 안 주면 `basic=outfit.jpg`. 조각 이름은 `<옷이름>_<종류>_<뼈>.png`.
   - 코드가 하는 일: 배경 지우기 → 캐논에 맞춰 정렬(ECC) → 캐논과 색이 다른 곳 = 옷 → 가까운 뼈로 나눔
     (가슴=윗옷, 윗팔=소매, 골반=치마/바지, 정강이=양말, 발=신발(빨강 등 신발 색)).
3. **뼈대 넣기**: `python3 tools/v3/make_skeleton.py public/v3-demo <out>` → `skeleton.json` 의 `outfits` 에 `{"<이름>": {"top":…, "bottom":…, "sleeve_l":…, …}}` 가 들어간다.
4. **검사**: `python3 tools/v3/check_v3.py public/v3-demo <qa> tools/v3/raw/canon.jpg`
   - `wave_seam_ok: true`(손 흔들기 25 프레임: 이음새 ≤6px 더, 손끝 무대 안), `fringe_ok: true`(흰 테두리 <1%)
   - `silhouette_iou ≥ 0.98`, `holes ≤ 2`, `joint_overlap_ok_8_12: true`, `skirt_covers_shorts: true`, 팔레트 ΔE p50 ≤ 10.
   - `<qa>/crops400.png`(관절 + 손 흔들기 25 프레임 어깨 400% 확대)를 눈으로 본다: 이음새·흰 테두리가 없어야 한다.
5. 390px 폰과 1280px 에서 손 흔들기까지 보고 PR.

Spine 으로 옮기기: `skeleton.json` 은 Spine JSON 모양(bones/slots/skins/animations). y 가 아래로 가므로 Spine 에선 y 와 rotation 부호를 뒤집는다.

## 손 흔들기 그림까지 함께 넣기
`--outfit 이름=옷.jpg,옷_흔들기.jpg` 처럼 쉼표 뒤에 "오른팔을 든" 옷 그림을 주면 흔들기 동작의 팔 조각(arm_up_r)도 그 옷으로 바뀝니다.
기본값: `basic=outfit_lines.jpg,outfit_wave.jpg`, 바탕 `body_lines_raw.jpg`, 흔들기 바탕 `body_wave.jpg`.
