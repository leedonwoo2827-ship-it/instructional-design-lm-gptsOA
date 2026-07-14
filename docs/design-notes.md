# 설계 노트

## 프롬프트 관리 (skills/)
- 모든 시스템 프롬프트는 [skills/](../skills/) 의 `SKILL.md` 로 관리한다. 코드([core/prompts.py](../core/prompts.py))는
  이 파일들을 읽어 조합만 한다. 프롬프트를 바꾸려면 해당 `SKILL.md` 를 편집하고 앱을 재시작한다.
- 편집 지점: 강의계획서=`skills/syllabus`, 교재=`skills/textbook`, PPT=`skills/slides`,
  점검=`skills/check-syllabus`·`skills/check-script`, 공통=`skills/gyosu-base`.

## LLM 백엔드 — ChatGPT 계정 OAuth (2026-07-14)
- 사내 LiteLLM 프록시를 제거하고, 사용자의 ChatGPT(Plus/Pro) 구독 계정으로 로그인해
  ChatGPT 백엔드 Responses API(`chatgpt.com/backend-api/wham`)를 사용한다. Codex CLI 와 동일한
  "Sign in with ChatGPT" PKCE 방식([core/oauth.py](../core/oauth.py), client_id·엔드포인트는 공개값).
- [core/llm.py](../core/llm.py) `ChatGPTOAuthProvider` 는 openai SDK 의 `responses.create` 를 커스텀
  base_url + `ChatGPT-Account-Id` 헤더로 호출하고, chat messages 를 instructions+input 으로 변환한다.
  토큰 만료 임박 시 선제 갱신, 401 시 refresh 후 1회 재시도. temperature 미사용(effort 로 제어).
- `gyosu-base` 의 **[출력 규칙 — 모든 모델 공통 엄수]** 로 섹션·순서·표 컬럼을 고정해 구조를 안정화한다.

## STEP 4 — 슬라이드 3갈래 (2026-07-14)
- **4-1** 개요(원고, 기존) → **②** 디자인 .pptx(사진·레이아웃, 기존).
- **4-2 노트북LM**: [core/slide_render.py](../core/slide_render.py) `build_render_code()` 가 **NotebookLM Studio
  ‘맞춤설정’용 렌더 코드**(`[SYSTEM KERNEL OVERRIDE]` + `## [Global Design System]` + `FUNCTION_0N_CALL_STUDIO()`)를
  생성. 총 장수를 청크(기본 20)로 나눠 함수 N개로 순차 생성. 정본 포맷 출처:
  odyssey-genvod-pptx/knowledge/notebooklm-slide-workflow.md. 디자인 시스템/강도는 같은 레포
  data/visual_styles.json 의 design_prompt·intensities 를 이식(NotebookLM 확정 4종). LLM 불필요(순수 템플릿).
- **4-3 비주얼 원고**: `skills/visual-brief` 프롬프트로 슬라이드별 아트디렉션 + JSON 스펙 생성. 사진 1순위,
  부실할 슬라이드는 `substitute:true` 로 표시해 도식·일러스트로 갈음. 개선 검색어는 ②·4-2 에 반영.

## 강의계획서 = 실무형(첨삭 반영)
- 표 중심의 간결한 실무형. 백워드설계·핵심이해·커리큘럼맵·인지수준 태그·과도한 이론 근거는 제거.
- 상세 규칙과 반영 이력은 [첨삭-로그.md](첨삭-로그.md) 및 각 `SKILL.md` 의 "첨삭 반영 규칙(누적)" 참조.

## 데이터/보안
- 산출물은 SQLite(`data/app.db`)에 프로젝트 단위로 저장(로컬, 커밋 제외).
- 회사 PPT 양식(`assets/company_template.pptx`), 원본 첨삭 자료(`_guideline/`), 키(`.env`·`data/user_settings.json`)는 커밋 제외.
