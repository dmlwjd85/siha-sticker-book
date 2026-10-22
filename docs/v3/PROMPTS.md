# 생성 프롬프트 틀 (GenerateImage, 무료)

공통: 참고 이미지 = `tools/v3/raw/body.jpg`(기본 몸, 마이크 포즈) 하나. 비율 9:16(720×1280). 배경은 한 색(흰색이나 연회색). 다른 회사 캐릭터 흉내 금지, 노출 금지.

## 공통 머리말
> Same character, same pose, same camera, same size and position as the reference image. Cute chibi-proportion anime girl, idol pose: her right hand (viewer's left) raised to chin height in a closed fist as if holding a microphone, elbow tucked to the side so the forearm does not cover the chest; the other arm relaxed down with a loose fist; feet apart. Clean cel shading, one shadow tone, outline color #6E3D5B, even 3px rounded lines. Plain flat light-gray background, no floor shadow, no text. Child-safe, modest.

## 기본 몸 (body.jpg)
> {공통 머리말} Plain light underwear-free base: simple white short-sleeve top and white shorts, no accessories, no hair (bald smooth head shape) or short tied hair.

## 손 흔드는 몸 (body_wave.jpg)
> {공통 머리말} Identical, except the lowered arm (viewer's right) is now raised beside the head, open palm waving, elbow bent. Mic hand unchanged.

## 옷 (outfit.jpg) / 손 흔드는 옷 (outfit_wave.jpg)
> {공통 머리말} She now wears: {윗옷}, {치마나 바지}, {양말}, {신발}. Keep skin, face, hands, mic-fist and body outline exactly the same. Colors: {HEX}.
흔드는 판은 참고 이미지를 `body_wave.jpg`로 바꾸고 같은 문장 + “sleeve follows the raised arm”.

## 머리카락 (hair.jpg / hair_wave.jpg)
> {공통 머리말} Add long wavy pink hair (#F4A6C4, shadow #E07FA6) with bangs; do not cover the eyes or the mic fist; hair behind the shoulders. Body and clothes unchanged.
흔드는 판은 `body_wave.jpg` 참고.

## 눈 감기 (eyes_closed.jpg)
> {공통 머리말} Identical image, only the eyes are gently closed (happy closed-eye arcs). Nothing else changes.

## 소품 (mic.jpg, accs.jpg — 따로 한 장)
> A single cute handheld microphone, silver ball head, pink handle, vertical, plain white background, outline #6E3D5B, cel shading, no hand, no text.
> Two small cute hair accessories on plain white background, separated: {장식 1}, {장식 2}.

나쁜 결과(다시 만들기): 자세·크기·손 위치가 바뀜, 주먹이 펴짐, 선 색이 검정, 배경 무늬, 손가락 개수 이상, 노출.
