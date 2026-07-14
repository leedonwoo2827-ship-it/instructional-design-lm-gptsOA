---
name: visual-brief
description: 슬라이드별 비주얼 원고(아트디렉션) — 사진 1순위, 사진이 부실할 슬라이드는 도식·일러스트로 갈음(대체)하도록 지시문·검색어를 설계.
---

[현재 과업: 비주얼 원고(아트디렉션) 작성]
제공된 '슬라이드 개요'의 각 슬라이드에 어떤 시각물이 들어가야 하는지 설계한다.
목적은 두 가지다: (1) 지금 자동 수집되는 사진이 주제와 겉돌거나 품질이 낮은 문제를
줄이도록 **구체적인 사진 검색 지시문**을 준다. (2) 좋은 사진을 찾기 어려운 슬라이드는
**도식·일러스트로 갈음(대체)** 하도록 표시한다.

[대원칙]
- **사진이 1순위.** 강의실·학생·교사·실험·기기·현장 장면처럼 실제 사진이 자연스러운
  슬라이드는 photo 로 두고, 막연한 단어('education') 대신 **주제·이론과 직접 연결된
  구체적 영어 검색어**를 준다. 예) 행동주의→'Pavlov classical conditioning dog experiment',
  인지주의→'human brain memory neurons diagram', 구성주의→'students collaborative
  project based learning classroom', 평가→'students taking written exam', 원격교육→
  'online video lecture student laptop'.
- **사진이 부실할 슬라이드만 대체.** 추상 개념·모형·절차·수치처럼 사진이 겉돌기 쉬운
  것은 `substitute:true` 로 표시하고, 어떤 도식/일러스트/차트인지 한 줄로 지시한다.
  (예: 프로세스 흐름도, 2×2 매트릭스, 개념 관계도, 막대/원 그래프)
- 표지·섹션 표지 슬라이드는 시각물 지시가 없어도 된다(생략 가능).

[출력 형식 — 두 부분]
1. **사람이 읽는 아트디렉션** (슬라이드별 2~4줄, 한국어):
   - `### 슬라이드 N — [제목]`
   - 권장 시각물 유형(photo / diagram / illustration / chart), 핵심 개념 한마디,
     사진이면 검색 지시문, 대체면 도식 형태와 담을 요소.
2. 맨 끝에 **기계가 읽는 JSON 블록**(코드펜스 ```json). 위 판단을 배열로 요약한다:

```json
[
  {"n":1,"visual":"photo","concept":"핵심 한마디","query":"concrete english query","substitute":false,"note":""},
  {"n":2,"visual":"diagram","concept":"ADDIE 5단계","query":"","substitute":true,"note":"좌→우 프로세스 흐름도, 5노드"}
]
```
- `n` 은 개요의 '슬라이드 N' 번호(표지 제외, 1부터).
- `substitute:true` 면 사진 대신 도식/일러스트를 렌더해 크롭한다는 뜻.
- JSON 은 개요에 존재하는 모든 본문 슬라이드를 빠짐없이 포함하고, 다른 말은 넣지 않는다.
