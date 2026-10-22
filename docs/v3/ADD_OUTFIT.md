# 옷 한 벌 더하기

1. `PROMPTS.md`의 틀로 `outfit.jpg`(쉬는 자세)와 `outfit_wave.jpg`(손 흔드는 자세) **두 장**을 만든다. 둘 다 없으면 흔들 때 소매가 몸에 남는다.
2. `tools/v3/raw/`에 `{이름}.jpg`, `{이름}_wave.jpg`로 넣고 `python3 tools/v3/build_v3.py && python3 tools/v3/make_skeleton.py` 실행. 결과는 `public/v3-demo/parts`, `skeleton.json`.
3. 확인: `npx vite preview --port 4179` 켠 뒤 `node tools/v3/check_frames.mjs` → `python3 tools/v3/check_frames.py /tmp/frames`. `"pass": true`여야 한다.

## 조각을 뼈에 붙이는 규칙
- **윗옷은 `fit_upper`(가슴 뼈), 아래옷·양말·신발은 `fit_lower`(허리 아래)**. 자르는 줄은 720 기준 y=640, 위·아래가 6px 겹친다(숨쉬기 때 틈 방지).
- **소매는 팔 뼈를 따른다.** 흔드는 쪽 소매는 쉬는 그림에 두지 말고 `outfit_wave`에서 가져와 `*_upper_wave`·`*_wave_arm_0~8` 조각에 넣는다. 팔뚝 휘기(−10°~10°, 9장)도 소매째 미리 만든다. 따로 떨어진 소매 조각을 만들지 않는다.
- **흔들기 전환은 바뀐 자리만.** 쉬는 그림과 흔드는 그림이 다른 곳(마스크 `dm`, x≥430·150<y<740)만 흔드는 그림으로 바꾼다. 마스크 밖이 달라지면 옷 그림을 다시 만든다.
- **마이크 손은 소품 뼈 `prop_r`.** 손잡이가 주먹 안에서 끝나게 하고, 주먹+팔뚝 조각(`hand_r`, 옷 제외)을 마이크 위에 그린다. 소매가 팔뚝까지 오면 그 소매도 `hand_r` 아래에 둔다.
- 머리카락이 어깨·소매에 닿는 곳은 쉬는 머리를 흔드는 머리 위에 덮어 흰 틈을 없앤다(`hair_back_wave`).
- 겹침은 아래 조각이 6px 이상 들어가게, 틈은 400%에서 0.

## 마감 점검
- 선 굵기 한결같음(검사기 `linewidth` 값이 쉬는 자세와 같음), 점·두 줄 선·후광 없음.
- 전 프레임 검사: 떨어진 조각, 얇은 틈, 상자 밖 변화, 남은 조각, 새 이음새 모두 0.
