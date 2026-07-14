# 교수설계 가이드 에이전트

강의 정보를 입력하면 **강의계획서 → 교재 · PPT 개요**를 생성하고, 실무 기준에 맞춰
**정렬 점검·직접 편집**까지 할 수 있는 Streamlit 앱입니다. 산출물은 프로젝트(강의) 단위로 자동 저장됩니다.

LLM 백엔드는 **ChatGPT 계정 OAuth(구독)** 로 연결합니다 — 사내 API 키 없이, 본인 **ChatGPT(Plus/Pro)** 계정으로
브라우저 로그인하면 ChatGPT 백엔드(Responses API)를 사용합니다. 모델·추론강도는 **좌측 사이드바 › 연결 설정**에서 선택합니다.

## 요구사항
- Python 3.10 ~ 3.13
- **ChatGPT(Plus/Pro) 구독 계정** — 사이드바에서 브라우저 OAuth 로그인
- 인터넷 연결(`auth.openai.com`, `chatgpt.com` 도달 가능)

## 설치 & 실행 (Windows)
1. **`setup.bat`** 더블클릭 — `.venv` 생성, 의존성 설치, `.env` 준비
2. **`run.bat`** 더블클릭 — 브라우저에서 `http://localhost:8701` 열림
3. 좌측 사이드바 **연결 설정 › ChatGPT 로그인** 클릭 → 브라우저에서 로그인 → 자동 연결
4. 사이드바 **강의 기본 정보** 입력 → **강의계획서 생성** → **STEP 2** 점검 → **STEP 3** 교재 → **STEP 4** 슬라이드

macOS / Linux: `./setup.sh` 후 `./run.sh`.

> 로그인 토큰은 `data/chatgpt_auth.json` 에 저장되며(커밋 금지), 만료 시 자동 갱신됩니다.

## 화면 구성
- **좌측 사이드바**: 강의 프로젝트(새로 만들기/열기/이름변경/삭제) · **강의 기본 정보**(입력 폼) · **연결 설정**(ChatGPT 로그인·모델·추론강도)
- **메인**: 상단 STEP 바(1·2·3·4) + 산출물 패널

## 사용 흐름
| 단계 | 내용 |
|---|---|
| **STEP 1 · 강의 정보** | 사이드바에 과목·대상·주차·방식·주제 입력 → **강의계획서** 생성(스트리밍) |
| **STEP 2 · 강의계획서** | 실무형 강의계획서 확인·수정·**직접 편집**. 아래 두 버튼: |
| | ① **정렬 점검 실행** — 생성물이 실무형 기준(섹션 구성·학습목표 3~4개·평가/출석 규정·주교재 서지·주별·과제)을 지키는지 **AI가 감사**해 ✅/⚠️/❌ 수정 제안을 문서 하단에 덧붙임 *(맞춤법 교정 아님)* |
| | ② **교재·슬라이드 작성으로 이동** — STEP 3로 이동. 점검을 먼저 하도록 ①이 강조되고, 점검 후 ②가 강조됨 |
| **STEP 3 · 교재** | 주차 선택 → **학생용 교재(읽기 자료)** 생성. 확인·수정·점검·직접 편집·저장 |
| **STEP 4 · 슬라이드 개요(원고)** | 주차 선택 → **개요(원고) 생성**(2단계: 제목 목록 → 상세, 시간당 20장 → 2시간 40장). 확인·수정·정렬 점검·직접 편집. MD/DOC/**개요 PPTX** 다운로드. |
| **STEP 5 · 노트북LM 렌더 코드** | 개요(원고)를 NotebookLM **소스**로 붙여넣고(‘전체 복사’ 지원), **NotebookLM 채팅에 붙여넣는 렌더 코드**를 생성합니다. 총 장수를 청크(기본 20)로 나눠 **BATCH**(자연어·권장) 또는 커널 오버라이드 형식으로 출력. **디자인 시스템**(플랫 벡터/인포그래픽/수채화/클레이메이션)·**강도**(은은/적당/풀)·**페이지 번호** 옵션. NotebookLM 이 흰 배경(#FFFFFF)·일관 스타일 슬라이드를 배치별로 생성합니다. |
| **STEP 6 · 비주얼 원고 · 디자인 PPTX** | ① **비주얼 원고**(슬라이드별 아트디렉션 + 사진 검색 지시문, 부실할 슬라이드는 도식으로 **갈음** 표시) · ② **이미지·레이아웃 정리** = 개요를 **디자인 PPTX**(사진 좌·우 배치, Openverse/Unsplash + 네이비+앰버)로 빌드 → **최종 PPTX + 이미지 출처(.txt)** 다운로드. 이 PPTX 에 STEP 5 의 NotebookLM 슬라이드를 SME 가 합칩니다. |

- 각 산출물은 `.md` / `.doc`(한글·워드) 저장, 슬라이드는 **개요 PPTX**(회사 양식 placeholder)와 **디자인 PPTX**(사진·도식 배치) 두 가지 지원.
- 강의계획서·교재·슬라이드 개요 모두 **직접 편집(마크다운)** 가능 — 편집본 기준으로 이후 AI 수정·디자인이 이어집니다.
- 디자인 슬라이드의 **로고**는 회사 양식(`assets/company_template.pptx`)의 **슬라이드 마스터**에 넣어두면 전 슬라이드에 상속됩니다(또는 `assets/logo.png` 를 두면 우상단 자동 삽입).

## 모델
ChatGPT 구독에서 사용할 모델 슬러그를 사이드바 연결 설정에서 선택 (기본 후보 **`gpt-5.5` / `gpt-5.4` / `gpt-5.4-mini`**):
- **계정마다 허용 모델이 다릅니다.** 로그인 후 **‘모델 목록 불러오기 (계정 기준)’** 버튼으로 실제 사용 가능한 슬러그를 받아 채우는 것을 권장합니다. 목록에 없으면 **직접 입력** 가능.
- **추론 강도(effort)**: `low` / `medium` / `high` — 개요·비주얼 원고는 medium, 디자인/렌더 플랜(JSON)은 자동 `low`(형식 안정성).

> 백엔드(Codex/ChatGPT 계정)는 일부 모델(예: `gpt-5.1`)을 거부할 수 있습니다. 400 오류가 나면 목록을 다시 불러와 지원되는 슬러그를 고르세요.

## 프롬프트 관리 (skills/)
프롬프트는 코드가 아니라 [skills/](skills/) 의 `SKILL.md` 로 관리합니다. 첨삭이 오면 해당 스킬 파일을
편집하고 앱을 재시작하면 반영됩니다. 자세한 내용은 [skills/README.md](skills/README.md), [docs/첨삭-로그.md](docs/첨삭-로그.md).

## 구조
```
app.py                 Streamlit UI (사이드바 입력 · STEP 1·2·3·4)
core/prompts.py        skills/*.md 로더 → 시스템 프롬프트 조합
core/oauth.py          ChatGPT 계정 OAuth(PKCE) 로그인·토큰 저장/갱신 (data/chatgpt_auth.json)
core/llm.py            ChatGPT 백엔드 Responses API 호출 (openai SDK, 스트리밍)
core/user_settings.py  설정 저장/로드 (data/user_settings.json, .env 기본값)
core/db.py             프로젝트(강의) 저장 SQLite (data/app.db)
core/viz.py            라인 아이콘 + Bloom 인지수준 SVG 차트
core/pptx_export.py    슬라이드 개요 → 개요 .pptx (회사 양식 placeholder 상속)
core/deck_builder.py   개요 → 디자인 .pptx (아트디렉터 LLM 패스 + 사진·도식·레이아웃 렌더)
core/slide_render.py   개요→플랜 → 흰 배경 1280×720 HTML 렌더 코드 청크 (4-2 노트북LM)
core/image_search.py   Openverse/Unsplash 이미지 검색·다운로드 + 출처 수집
skills/                교수설계 프롬프트(SKILL.md) — 첨삭 반영 지점 (slides · visual-brief 등)
assets/company_template.pptx  회사 PPT 양식(선택, 로컬) · assets/logo.png(선택)
setup.bat / run.bat    Windows 설치·실행 (setup.sh / run.sh: mac·linux)
```

## 보안
- 로그인 토큰·프로젝트 DB·회사 양식·원본 첨삭 자료는 **`.gitignore` 로 커밋에서 제외**됩니다
  (`.env`, `data/chatgpt_auth.json`, `data/user_settings.json`, `data/app.db`, `assets/*.pptx`, `_context/`, `_assets/`, `_guideline/`).
- ChatGPT 로그인은 Codex CLI 와 동일한 "Sign in with ChatGPT" OAuth 방식이며, 토큰은 로컬에만 저장됩니다.

## 설정 우선순위
`data/user_settings.json`(사이드바 저장값) > `.env` 환경변수 > 코드 기본값

## 문의
fedu@ubion.co.kr
