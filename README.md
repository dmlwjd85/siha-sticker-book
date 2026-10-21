# 시하 스티커북

시하에게 옷과 스티커를 끌어다 붙여 꾸미는 웹 스티커북입니다. 휴대폰에 앱처럼 설치할 수 있는 PWA이고, 광고·계정·데이터 수집이 없습니다.

- 바로 쓰기: https://dmlwjd85.github.io/siha-sticker-book/
- 저장: 브라우저 `localStorage` 키 `siha-sticker-book-v1`(예전 `bgw/siha` 주소와 같은 github.io 출처라 저장이 그대로 이어짐). 저장 버튼은 PNG로 내려받기.
- `bgw` 저장소의 `siha-dress-book/`, `siha/`, `tools/sticker_fit/`, `tools/build_sticker_assets.py` 에서 git 기록과 함께 옮겨 왔습니다(옛 드레스 북 `#dress`는 빼고).

## 구조

```
index.html                 앱 셸(아이콘·manifest·글꼴)
vite.config.js             base '/siha-sticker-book/', 빌드 후 sw.js 캐시 목록·버전 주입
src/main.jsx               시작점(서비스 워커 등록, 보호자 확인 개인정보 링크)
src/sticker/               스티커북 화면
  StickerBook.jsx          끌기·놓기·저장·불러오기(예전 저장본 이전 포함)
  model.js                 부품 목록, 레이어 순서, 겹침 규칙(hide/replace/onlyWith/unlessSlot/hideSlots)
  data/layers.json         레이어 순서와 슬롯
  data/characters/*.json   캐릭터(몸 조각, 장식 자리)
  data/parts/<id>.json     부품 하나 = JSON 하나
  data/backgrounds/        배경 목록
public/sticker/x4/*.png    부품 그림(스테이지 1단위 = 4px)
public/sticker/bg/*.jpg    배경
public/manifest.webmanifest, public/sw.js, public/icons/   PWA
tools/build_sticker_assets.py, tools/sticker_fit/          원본 PNG → 부품 그림·JSON 다시 만들기
scripts/generate-icons.py  앱 아이콘 다시 만들기
docs/                      부품 추가·수동 작업 안내
```

## 새 부품 추가 (JSON + PNG)

1. 투명 PNG를 `public/sticker/x4/<id>.png`에 넣습니다. 스테이지(360×650) 기준 크기의 4배로 만듭니다.
2. `src/sticker/data/parts/<id>.json`을 만듭니다.

```json
{
  "id": "skirt_new",
  "name": "새 치마",
  "category": "bottom",
  "slot": "bottom",
  "layer": "bottom",
  "pieces": [{ "src": "x4/skirt_new.png", "x": 110, "y": 300, "w": 140, "h": 100 }],
  "occlusion": { "hideCharacterPieces": [], "clearsSlots": ["dress"] }
}
```

- `x, y, w, h`는 스테이지 단위이고, 몸에 맞는 처음 자리입니다. 트레이에서 누르면 이 자리에 붙습니다.
- 장식(리본·꽃 등)은 `"multi": true, "anchors": ["crown", ...], "size": {"w","h"}`를 씁니다.
- JSON 파일은 자동으로 읽힙니다(`import.meta.glob`). 코드는 고치지 않아도 됩니다. 자세한 내용은 `docs/부품-추가하기.md`에 있습니다.
3. `npm test`, `npm run dev`로 확인합니다.

원본 시트에서 다시 만들 때는 `python3 tools/build_sticker_assets.py`(ESRGAN 모델 `tools/sticker_fit/README.md` 참고)를 씁니다. 원본 파일은 고치지 않고 복사본만 만듭니다.

## 빌드

```bash
npm ci
npm run dev      # http://localhost:5178/siha-sticker-book/
npm test
npm run build    # dist/ (sw.js에 캐시 버전·목록 자동 주입)
```

## 배포(릴리스)

- 지금은 `gh-pages` 브랜치에서 GitHub Pages를 내보냅니다. 배포 순서는 이렇습니다.
  ```bash
  npm ci && npm test && npm run build
  npx gh-pages -d dist      # 또는 dist/ 내용을 gh-pages 브랜치에 커밋·push
  ```
- 자동 배포 워크플로는 `docs/ci/deploy.yml`에 준비해 두었습니다. `workflow` 권한이 있는 계정으로 `.github/workflows/deploy.yml`로 옮겨 push하고, 저장소 Settings → Pages의 Source를 "GitHub Actions"로 바꾸면 `main`에 push할 때마다 테스트 → 빌드 → 배포가 자동으로 됩니다.
- 기능 작업은 브랜치 → PR → 확인 후 `main`에 머지합니다.
- 서비스 워커는 빌드마다 새 캐시 버전을 써서 설치된 앱도 다음 실행 때 새 버전을 받습니다.
- 되돌리기: 문제가 있는 커밋을 `git revert` 해서 `main`에 push합니다.
