# -*- coding: utf-8 -*-
"""교수설계 가이드 에이전트 — Streamlit + ChatGPT 계정 OAuth(구독).

원본 _context/교수설계-에이전트.html 의 화면 구성(상단 STEP 바 · 좌측 입력 / 우측 출력
2단 레이아웃)과 브랜드 디자인을 이식했다.

호출 경로: Streamlit → openai SDK(responses) → ChatGPT 백엔드(chatgpt.com/backend-api/wham).
로그인은 사이드바 '연결 설정 › ChatGPT 로그인'(브라우저 OAuth), 토큰은 core/oauth.py 가
data/chatgpt_auth.json 에 관리. 모델·추론강도는 사이드바에서 선택.
STEP 4: 4-1 개요 → ② 디자인 PPT · 4-2 노트북LM 렌더 코드 · 4-3 비주얼 원고.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import markdown as md_lib
import streamlit as st
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")  # 메모장 저장 .env 의 BOM 허용

from core import db  # noqa: E402
from core import deck_builder  # noqa: E402
from core import image_search  # noqa: E402
from core import llm as llm_mod  # noqa: E402
from core import oauth  # noqa: E402
from core import prompts  # noqa: E402
from core import slide_render  # noqa: E402
from core import user_settings as settings_mod  # noqa: E402
from core.pptx_export import outline_to_pptx  # noqa: E402
from core.viz import (  # noqa: E402
    ICON_DOC, ICON_INFO, ICON_SLIDE, bloom_chart_html, bloom_counts,
)

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

# 회사 PPT 양식(.pptx) — 있으면 PPTX 생성 시 테마·마스터를 상속. (커밋 제외)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TEMPLATE_PATH = ASSETS_DIR / "company_template.pptx"
LOGO_PATH = ASSETS_DIR / "logo.png"


def template_arg():
    return str(TEMPLATE_PATH) if TEMPLATE_PATH.exists() else None

st.set_page_config(
    page_title="교수설계 가이드 에이전트",
    page_icon="교",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _init_db():
    db.init_db()
    return True


_init_db()

# 밝은 에디토리얼 디자인 (Figma design.md 기반: 흰 캔버스·헤어라인·알약 버튼·파스텔·그림자 최소)
_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
:root{
  --canvas:#ffffff; --bg:#fbfbfd; --ink:#141518; --ink2:#5b6472;
  --line:#ececee; --line-soft:#f2f2f4;
  --brand:#3b4ec8; --brand2:#2c3aa0; --brand-soft:#eef0fb;
  --lilac:#efeaff; --lime:#eef6dd; --cream:#fbf3e6; --mint:#e6f6ef;
  --ok:#0e9f6e; --warn:#b45309; --err:#cc4117;
}
html,body,.stApp,[class*="css"]{font-family:'Pretendard',-apple-system,'Malgun Gothic',sans-serif;}
.stApp{background:var(--bg);}
[data-testid="stHeader"]{background:transparent;}
/* 사이드바 넓게 — 접힘(aria-expanded=false) 시 완전히 숨겨 삐짐 방지 */
[data-testid="stSidebar"]{min-width:460px;max-width:460px;}
[data-testid="stSidebar"][aria-expanded="false"]{min-width:460px;max-width:460px;margin-left:-460px;}
.block-container{max-width:1240px;padding-top:1rem;padding-bottom:4rem;}

/* 헤더 — 밝은 에디토리얼(그라데이션 로고 제거) */
.ida-header{background:var(--canvas);border:1px solid var(--line);border-radius:20px;
  padding:18px 22px;margin-bottom:14px;box-shadow:none;}
.ida-eyebrow{font-family:'SF Mono','JetBrains Mono',Consolas,monospace;font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink2);margin-bottom:5px;}
.ida-title{font-weight:800;font-size:22px;letter-spacing:-0.03em;color:var(--ink);line-height:1.1;}
.ida-sub{font-size:13px;color:var(--ink2);margin-top:4px;}
.ida-panel-title{font-weight:700;font-size:14.5px;color:var(--ink);margin:2px 0 10px;
  letter-spacing:-0.01em;display:flex;align-items:center;}

/* 카드·컨테이너·expander — 헤어라인, 그림자 없음 */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:20px;border-color:var(--line)!important;}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:16px;background:var(--canvas);
  box-shadow:none;margin-bottom:12px;}
[data-testid="stExpander"] summary{font-weight:700;color:var(--ink);}
[data-testid="stExpander"] summary:hover{color:var(--brand);}

/* 버튼 — 알약(pill) */
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{
  border-radius:999px;font-weight:600;border:1px solid var(--line);background:var(--canvas);
  color:var(--ink);transition:.15s;}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--brand);color:var(--brand);}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"],
.stFormSubmitButton>button[kind="primaryFormSubmit"]{
  background:var(--brand);border-color:var(--brand);color:#fff;}
.stButton>button[kind="primary"]:hover,.stFormSubmitButton>button[kind="primary"]:hover,
.stFormSubmitButton>button[kind="primaryFormSubmit"]:hover{
  background:var(--brand2);border-color:var(--brand2);color:#fff;}

/* 입력 */
.stTextInput input,.stTextArea textarea{border-radius:10px;border-color:var(--line);background:var(--canvas);}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--brand);box-shadow:none;}

/* 안내/정보 박스 — 파스텔 블록(Figma 시그니처) */
[data-testid="stAlertContainer"]{border-radius:16px;border:none;}

/* 교재/PPT 탭 — 알약 */
[data-baseweb="tab-list"]{gap:8px;border-bottom:none;}
[data-baseweb="tab"]{background:var(--canvas);border:1px solid var(--line)!important;border-radius:999px;
  padding:6px 16px;font-weight:600;}
[data-baseweb="tab"][aria-selected="true"]{background:var(--brand);color:#fff;border-color:var(--brand)!important;}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none!important;}

/* 산출물 마크다운 */
[data-testid="stMarkdownContainer"] h1{font-size:24px;letter-spacing:-0.02em;border-bottom:1px solid var(--line);padding-bottom:8px;}
[data-testid="stMarkdownContainer"] h2{font-size:18px;letter-spacing:-0.015em;color:var(--ink);margin-top:24px;}
[data-testid="stMarkdownContainer"] h3{font-size:15px;}
[data-testid="stMarkdownContainer"] table{border-collapse:collapse;width:100%;font-size:13px;margin:12px 0;}
[data-testid="stMarkdownContainer"] th{background:var(--lilac);color:var(--ink);font-weight:700;text-align:left;}
[data-testid="stMarkdownContainer"] th,[data-testid="stMarkdownContainer"] td{border:1px solid var(--line);padding:8px 11px;}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td{background:#fafafa;}
[data-testid="stMarkdownContainer"] blockquote{border-left:3px solid var(--brand);background:var(--brand-soft);
  padding:8px 14px;border-radius:0 10px 10px 0;}
[data-testid="stMarkdownContainer"] code{background:#f2f2f4;border-radius:5px;padding:1px 5px;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

WEEK_CHOICES = [8, 10, 13, 15, 16]
MODE_CHOICES = ["대면", "온라인(실시간)", "온라인(비동기·동영상)", "혼합(블렌디드)", "플립러닝"]
STEP_META = [
    (1, "강의 정보 입력", "과목 · 대상 · 운영 방식"),
    (2, "강의계획서", "목표–평가–주차 정렬"),
    (3, "교재", "학생용 읽기 자료"),
    (4, "슬라이드 개요", "원고(개요) 생성"),
    (5, "노트북LM 코드", "렌더 코드 생성"),
    (6, "비주얼·PPTX", "사진 갈음 · 디자인 PPTX"),
]
REFINE_TMPL = (
    "다음 요청대로 수정하여, 수정된 문서 전체를 다시 출력해 주세요. "
    "수정 시에도 학습목표 정렬 원칙(측정 가능 동사, 목표–평가–활동 인지수준 일치)을 유지하세요.\n\n요청: {req}"
)

# 교재/PPT(장문·다수 슬라이드)는 넉넉한 토큰으로 생성(추론 모델 잘림 방지). 설정값보다 크면 그 값 사용.
GEN_MAX_TOKENS = 16000
SLIDE_LIST_TOKENS = 3000      # 슬라이드 제목 목록(1단계)
SLIDE_EXPAND_TOKENS = 24000   # 슬라이드 상세(2단계, 다수 슬라이드)
SLIDES_PER_HOUR = 20          # 1시간당 슬라이드 수
# 검색어가 없는 슬라이드용 폴백(교육 일반, 로테이션으로 중복 최소화). 내용 불일치는 SME가 갈음.
_FALLBACK_IMG_QUERIES = [
    "university lecture classroom students", "teacher explaining whiteboard classroom",
    "students group discussion table", "college students studying laptop",
    "online learning video lecture student", "team collaboration meeting",
    "books notebook study desk", "presentation projector classroom",
]


# ---------------------------------------------------------------------------
# 세션 상태
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("settings", settings_mod.load())
ss.setdefault("step", 1)
ss.setdefault("project_id", None)     # 현재 프로젝트(강의) DB id
ss.setdefault("syllabus_md", "")
ss.setdefault("syllabus_msgs", [])
ss.setdefault("script_week", 1)
ss.setdefault("script_doc_md", "")   # 교재
ss.setdefault("script_ppt_md", "")   # PPT 개요
ss.setdefault("script_doc_msgs", [])
ss.setdefault("script_ppt_msgs", [])
ss.setdefault("ping_status", None)
ss.setdefault("form", {})
ss.setdefault("had_login", oauth.is_logged_in())
ss.setdefault("deck_bytes", None)     # ②이미지·레이아웃 정리 결과(.pptx 바이트)
ss.setdefault("credits_txt", "")      # 이미지 출처 텍스트
ss.setdefault("deck_name", "")        # 디자인 덱 파일명
ss.setdefault("img_cache", {})        # 검색어→(bytes,credit) 세션 캐시
ss.setdefault("render_code", "")         # 4-2 노트북LM: Studio 맞춤설정용 렌더 코드(스크립트)
ss.setdefault("render_total", 0)         # 총 슬라이드(0=개요에서 자동 감지)
ss.setdefault("render_per_chunk", 20)    # 한 번에(청크) 생성할 장수 → FUNCTION 개수 결정
ss.setdefault("render_design", slide_render.DEFAULT_DESIGN)  # 디자인 시스템 프리셋
ss.setdefault("render_intensity", slide_render.DEFAULT_INTENSITY)  # 스타일 강도
ss.setdefault("render_format", slide_render.DEFAULT_FORMAT)  # 출력 형식(batch/kernel)
ss.setdefault("render_pagenum", True)                        # 페이지 번호 지시 포함
ss.setdefault("visual_brief_md", "")     # 4-3 비주얼 원고(아트디렉션)
ss.setdefault("visual_brief_msgs", [])
ss.setdefault("model_options", [])       # 계정 기준으로 불러온 모델 슬러그 목록


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def ensure_ready() -> bool:
    if not oauth.is_logged_in():
        st.warning("좌측 사이드바 '연결 설정'에서 **ChatGPT 로그인**을 눌러 계정을 연결하세요.")
        return False
    return True


def clear_artifacts() -> None:
    ss.form = {}
    ss.syllabus_md, ss.syllabus_msgs = "", []
    ss.script_doc_md, ss.script_ppt_md = "", ""
    ss.script_doc_msgs, ss.script_ppt_msgs = [], []
    ss.deck_bytes, ss.credits_txt, ss.deck_name = None, "", ""
    ss.render_code, ss.visual_brief_md, ss.visual_brief_msgs = "", "", []
    ss.script_week, ss.step = 1, 1


def load_project_into_session(pid: int) -> None:
    p = db.load_project(pid)
    if not p:
        return
    ss.project_id = p["id"]
    ss.form = p["form"] or {}
    ss.syllabus_md, ss.syllabus_msgs = p["syllabus_md"], p["syllabus_msgs"]
    ss.script_week = p["script_week"] or 1
    ss.script_doc_md, ss.script_doc_msgs = p["script_doc_md"], p["script_doc_msgs"]
    ss.script_ppt_md, ss.script_ppt_msgs = p["script_ppt_md"], p["script_ppt_msgs"]
    ss.deck_bytes, ss.credits_txt, ss.deck_name = None, "", ""
    ss.render_chunks, ss.visual_brief_md, ss.visual_brief_msgs = [], "", []


def persist() -> None:
    """현재 세션 산출물을 DB에 저장(프로젝트 없으면 과목명으로 자동 생성). 이름은 건드리지 않음."""
    if not ss.project_id:
        name = (ss.form.get("title") or "").strip() or "새 강의"
        ss.project_id = db.create_project(name)
    db.save_project(
        ss.project_id,
        form=ss.form,
        syllabus_md=ss.syllabus_md, syllabus_msgs=ss.syllabus_msgs,
        script_week=ss.script_week,
        script_doc_md=ss.script_doc_md, script_doc_msgs=ss.script_doc_msgs,
        script_ppt_md=ss.script_ppt_md, script_ppt_msgs=ss.script_ppt_msgs,
    )


def stream_into(placeholder, system: str, messages: list, label: str = "생성",
                max_tokens: int = None) -> str:
    provider = llm_mod.build_provider(ss.settings)
    mt = max(max_tokens or 0, ss.settings.max_tokens)
    full = ""
    placeholder.markdown("**작성 중…** 잠시만 기다려 주세요. 내용이 이 영역에 실시간으로 나타납니다. ▌")
    t0 = time.time()
    last = 0
    print(f"[{label}] 시작 · 모델={ss.settings.model} · max_tokens={mt}", flush=True)
    try:
        for delta in provider.stream(system, messages,
                                     max_tokens=mt,
                                     temperature=ss.settings.temperature):
            full += delta
            placeholder.markdown(full + " ▌")
            if len(full) - last >= 400:
                last = len(full)
                print(f"[{label}] …{len(full):,}자 생성 중 ({time.time() - t0:.0f}s)", flush=True)
        placeholder.markdown(full)
        print(f"[{label}] 완료 · {len(full):,}자 · {time.time() - t0:.1f}s", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] 오류: {type(e).__name__}: {e}", flush=True)
        st.error(f"생성 실패: {type(e).__name__}: {e}\n\n사내망 연결과 API 키를 확인하세요.")
        if full:
            placeholder.markdown(full)
    return full


def md_to_doc_bytes(md_text: str) -> bytes:
    body = md_lib.markdown(md_text or "", extensions=["tables", "fenced_code"])
    html = (
        "<html xmlns:o='urn:schemas-microsoft-com:office:office' "
        "xmlns:w='urn:schemas-microsoft-com:office:word'><head><meta charset='utf-8'>"
        "<style>body{font-family:'Malgun Gothic',sans-serif;font-size:11pt;line-height:1.6}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:5pt;font-size:10pt}"
        "th{background:#eef}h1{font-size:16pt}h2{font-size:13pt;color:#2c3aa0}h3{font-size:11.5pt}</style>"
        f"</head><body>{body}</body></html>"
    )
    return ("﻿" + html).encode("utf-8")


def syllabus_user_msg(f: dict) -> str:
    return (
        "다음 강의 정보로 강의계획서를 작성해 주세요.\n\n"
        f"과목명: {f.get('title') or '[입력 필요]'}\n"
        f"학문 분야: {f.get('field') or '-'}\n"
        f"수강 대상: {f.get('target') or '[입력 필요]'}\n"
        f"학점/시수: {f.get('credit') or '-'}\n"
        f"총 주차: {f.get('weeks')}주\n"
        f"강의 방식: {f.get('mode')}\n"
        f"주요 내용·주제: {f.get('topics') or '-'}\n"
        f"수강생 특성: {f.get('learner') or '-'}\n"
        f"평가 선호·수업 철학: {f.get('policy') or '-'}"
    )


def session_hours() -> int:
    try:
        return int(ss.form.get("hours", 2) or 2)
    except (TypeError, ValueError):
        return 2


def script_user_msg(week: int, fmt: str, note: str, syllabus_md: str) -> str:
    kind = "학생용 교재(읽기 자료)" if fmt == "doc" else "PPT 슬라이드 개요"
    extra = f"\n[교수자 추가 요청] {note}\n" if note.strip() else ""
    vol = ""
    if fmt == "ppt":
        h = session_hours()
        vol = (f"\n이 차시는 약 {h}시간 수업입니다. 슬라이드는 1시간당 약 {SLIDES_PER_HOUR}장 기준, "
               f"표지 제외 본문 약 {h * SLIDES_PER_HOUR}장으로 작성하세요. 발표자 노트는 넣지 마세요.")
    return (
        f"아래는 확정된 강의계획서입니다. 이 계획서의 {week}주차에 대한 {kind}를 작성해 주세요. "
        f"반드시 계획서의 해당 주차 목표와 강좌 목표(G#)를 상속하세요.{extra}{vol}\n"
        f"=== 강의계획서 ===\n{syllabus_md}"
    )


def out_name(kind: str) -> str:
    """kind: 'syllabus' | '교재' | 'PPT개요'"""
    title = (ss.form.get("title") or "강의").strip() or "강의"
    if kind == "syllabus":
        return f"{title}_강의계획서"
    return f"{title}_{ss.script_week}주차_{kind}"


def run_pending(pending: dict, placeholder) -> None:
    """예약된 생성/수정/점검을 우측 placeholder 에 실행. doc: syllabus | script_doc | script_ppt."""
    kind, doc = pending["kind"], pending["doc"]
    if doc == "syllabus":
        if kind == "check":
            msgs = [{"role": "user", "content": f"다음 산출물을 점검해 주세요.\n\n{ss.syllabus_md}"}]
            rep = stream_into(placeholder, prompts.SYS_CHECK_SYL, msgs, label="강의계획서 점검")
            if rep:
                ss.syllabus_md += f"\n\n---\n\n## 정렬 점검 보고\n\n{rep}"
        else:
            full = stream_into(placeholder, prompts.SYS_SYLLABUS, ss.syllabus_msgs, label="강의계획서")
            if full:
                ss.syllabus_md = full
                ss.syllabus_msgs.append({"role": "assistant", "content": full})
        return

    # script_doc(교재) | script_ppt(PPT 개요)
    is_doc = doc == "script_doc"
    md_key = "script_doc_md" if is_doc else "script_ppt_md"
    msgs_key = "script_doc_msgs" if is_doc else "script_ppt_msgs"
    wk = f"{ss.script_week}주차 " + ("교재" if is_doc else "PPT 개요")

    # ── PPT 생성: 2단계(제목 목록 → 상세)로 슬라이드 개수 보장 ──
    if (not is_doc) and kind == "gen":
        n = session_hours() * SLIDES_PER_HOUR
        provider = llm_mod.build_provider(ss.settings)
        placeholder.markdown(f"**슬라이드 목록 구성 중…** (목표 {n}장)")
        list_user = (
            f"'{ss.script_week}주차' 강의를 정확히 {n}장 슬라이드로 구성합니다. "
            f"도입(2~3장) · 선수지식(1~2장) · 개념 설명(대부분, 개념마다 정의·예시·비교·적용으로 여러 장 분절) "
            f"· 사례/활동 · 형성평가(1~2장) · 요약·예고(1~2장) 순서로, "
            f"슬라이드 {n}개의 '제목'만 1.부터 {n}.까지 번호 목록으로 출력하세요. "
            f"정확히 {n}줄, 제목 외 다른 말은 쓰지 마세요.\n\n=== 강의계획서 ===\n{ss.syllabus_md}"
        )
        try:
            titles = provider.generate(
                "너는 슬라이드 제목 목록만 출력한다. 머리말·설명 없이 '1. 제목' 형식 번호 목록만.",
                [{"role": "user", "content": list_user}],
                max_tokens=SLIDE_LIST_TOKENS, temperature=0.4)
        except Exception as e:  # noqa: BLE001
            print(f"[슬라이드 목록] 오류: {e}", flush=True)
            titles = ""
        exp_user = (
            f"아래 슬라이드 제목 목록({n}장)의 **모든 {n}개** 슬라이드를 각각 상세 개요로 작성하세요. "
            f"반드시 {n}개의 '### 슬라이드 N — 제목' 블록을 만들고, 각 블록에 "
            f"- 레이아웃 제안(섹션 표지/2단/콘텐츠) / - 핵심 메시지(1개) / - 본문 개요(불릿 3~5개)를 넣으세요. "
            f"발표자 노트는 넣지 마세요. 맨 앞에 차시 학습목표와 슬라이드 구성 개요 표도 포함하세요.\n\n"
            f"[슬라이드 제목 목록]\n{titles}\n\n[강의계획서]\n{ss.syllabus_md}"
        )
        msgs = [{"role": "user", "content": exp_user}]
        full = stream_into(placeholder, prompts.SYS_SCRIPT_PPT, msgs, label=wk, max_tokens=SLIDE_EXPAND_TOKENS)
        if full:
            ss[md_key] = full
            ss[msgs_key] = msgs + [{"role": "assistant", "content": full}]
        return

    sys_gen = prompts.SYS_SCRIPT_DOC if is_doc else prompts.SYS_SCRIPT_PPT
    if kind == "check":
        cur = ss[md_key]
        msgs = [{"role": "user", "content": f"다음 산출물을 점검해 주세요.\n\n{cur}"}]
        rep = stream_into(placeholder, prompts.SYS_CHECK_SCR, msgs, label=f"{wk} 점검")
        if rep:
            ss[md_key] = cur + f"\n\n---\n\n## 정렬 점검 보고\n\n{rep}"
    else:  # 교재 gen | refine(교재·PPT)
        full = stream_into(placeholder, sys_gen, ss[msgs_key], label=wk, max_tokens=GEN_MAX_TOKENS)
        if full:
            ss[md_key] = full
            ss[msgs_key].append({"role": "assistant", "content": full})


def run_design(status) -> None:
    """②이미지·레이아웃 정리: 개요(md) → 아트디렉터 플랜 → 이미지 → 디자인 .pptx.

    결과를 ss.deck_bytes / ss.credits_txt / ss.deck_name 에 저장. 실패는 그레이스풀.
    """
    outline = ss.script_ppt_md
    if not outline.strip():
        st.warning("먼저 ① 슬라이드 개요를 생성하세요.")
        return
    # 구조화(JSON) 작업은 형식 안정성이 중요 → 추론 강도를 낮춰(low) 생성한다.
    provider = llm_mod.build_provider(ss.settings)
    provider.effort = "low"
    print(f"[design] 아트디렉터 모델={provider.model} · effort=low", flush=True)

    def gen_fn(system, user, mt):
        return provider.generate(system, [{"role": "user", "content": user}], max_tokens=mt)

    deck_title = out_name("슬라이드")
    subtitle = f"{ss.script_week}주차 · {(ss.form.get('title') or '강의').strip()}"
    status.markdown("**① 슬라이드 구성 분석 중…** (레이아웃·사진 배치 결정)")
    plan = deck_builder.plan_from_outline(gen_fn, outline, deck_title, subtitle=subtitle)

    # 요청: 모든 본문 슬라이드에 사진 1장씩(좌우 교차 배치). 내용 불일치는 SME가 갈음.
    # 검색어 우선순위: 비주얼 원고(영문 쿼리) > 아트디렉터 image_query > 폴백 로테이션.
    # 표지(index 0)만 제외하고 전부 photo 로 강제하되, 본문 텍스트(bullets)는 보존한다.
    briefs = slide_render.parse_visual_brief(ss.visual_brief_md)
    for i in range(1, len(plan)):
        s = plan[i]
        if not s.get("bullets"):  # cards/compare/table → 텍스트 살려 photo 본문으로
            filled = []
            for it in (s.get("items") or []):
                lbl, desc = it.get("label", ""), it.get("desc", "")
                if lbl or desc:
                    filled.append(f"{lbl} — {desc}" if (lbl and desc) else (lbl or desc))
            if not filled and s.get("lines"):
                filled = list(s["lines"])
            if filled:
                s["bullets"] = filled[:5]
        q = ((briefs.get(i) or {}).get("query") or "").strip() or (s.get("image_query") or "").strip()
        if not q:
            q = _FALLBACK_IMG_QUERIES[i % len(_FALLBACK_IMG_QUERIES)]
        s["type"] = "photo"
        s["image_query"] = q

    queries = deck_builder.image_queries(plan)
    images = {}
    if queries:
        bar = st.progress(0.0, text=f"주제 사진 수집 중… (0/{len(queries)})")
        _ukey = (ss.settings.unsplash_key or "").strip()
        for k, (idx, q) in enumerate(queries.items(), 1):
            data, credit = image_search.fetch(q, cache=ss.img_cache, unsplash_key=_ukey)
            if not data:  # 좁은 검색어가 0건이면 폴백으로 재시도 → 페이지마다 사진 보장
                fb = _FALLBACK_IMG_QUERIES[idx % len(_FALLBACK_IMG_QUERIES)]
                data, credit = image_search.fetch(fb, cache=ss.img_cache, unsplash_key=_ukey)
            if data:
                images[idx] = data
                plan[idx]["_credit"] = credit
            else:
                print(f"[design] 슬라이드 {idx + 1}: 사진 검색 실패(q='{q}')", flush=True)
            bar.progress(k / len(queries), text=f"주제 사진 수집 중… ({k}/{len(queries)})")
        bar.empty()

    status.markdown("**슬라이드 빌드 중…** (네이비+앰버 레이아웃 적용)")
    data = deck_builder.build_deck(
        plan, template_path=template_arg(), images=images, deck_title=deck_title,
        logo_path=str(LOGO_PATH) if LOGO_PATH.exists() else None)
    if not data:
        st.error("슬라이드 빌드 실패(python-pptx 확인).")
        return
    entries = [(i + 1, plan[i].get("_credit")) for i in sorted(images.keys())]
    ss.deck_bytes = data
    ss.deck_name = deck_title
    ss.credits_txt = image_search.credits_text(f"{deck_title} — 이미지 출처 (CC 라이선스)", entries)
    n_pic = len(images)
    status.markdown(f"**완료** — {len(plan)}장 · 사진 {n_pic}장 삽입. 아래에서 내려받으세요.")


def run_visual_brief(placeholder) -> None:
    """4-3 비주얼 원고: 개요(4-1)를 받아 슬라이드별 아트디렉션 + JSON 스펙 생성."""
    outline = ss.script_ppt_md
    if not outline.strip():
        st.warning("먼저 ① 4-1 슬라이드 개요를 생성하세요.")
        return
    msgs = [{"role": "user", "content":
             f"아래 슬라이드 개요의 비주얼 원고(아트디렉션)를 작성하세요. "
             f"사진 검색 지시문과, 사진이 부실할 슬라이드의 대체 도식 지시를 포함하고, "
             f"맨 끝에 JSON 블록을 넣으세요.\n\n=== 슬라이드 개요 ===\n{outline}"}]
    full = stream_into(placeholder, prompts.SYS_VISUAL_BRIEF, msgs,
                       label="비주얼 원고", max_tokens=SLIDE_EXPAND_TOKENS)
    if full:
        ss.visual_brief_md = full
        ss.visual_brief_msgs = msgs + [{"role": "assistant", "content": full}]


def run_render_code() -> int:
    """4-2 노트북LM: 총 장수·청크·디자인으로 Studio 렌더 코드 생성(LLM 불필요, 즉시).

    반환: 사용된 총 슬라이드 수(0=개요 없음).
    """
    total = int(ss.render_total or 0) or slide_render.count_slides(ss.script_ppt_md)
    if total < 1:
        return 0
    ss.render_code = slide_render.build_render_code(
        total, per_chunk=int(ss.render_per_chunk or slide_render.DEFAULT_PER_CHUNK),
        design_key=ss.render_design, intensity_key=ss.render_intensity,
        fmt=ss.render_format, page_numbers=bool(ss.render_pagenum))
    ss.deck_name = ss.deck_name or out_name("슬라이드")
    return total


def script_downloads(md_key, doc_key, is_ppt, busy=False):
    """탭/스텝 상단 다운로드 버튼 → (본문 placeholder, 컨트롤 container) 반환.

    busy=True(생성/수정/점검 진행 중)면 다운로드 버튼·요약을 감춘다(작성 중엔 노출 X).
    """
    cur = ss[md_key]
    fn = out_name("PPT개요" if is_ppt else "교재")
    if cur and not busy:
        dc = st.columns([1, 1, 1, 6]) if is_ppt else st.columns([1, 1, 7])
        dc[0].download_button("MD", cur, file_name=fn + ".md", mime="text/markdown",
                              key=f"md_{doc_key}", use_container_width=True)
        dc[1].download_button("DOC", md_to_doc_bytes(cur), file_name=fn + ".doc",
                              mime="application/msword", key=f"doc_{doc_key}", use_container_width=True)
        if is_ppt:
            pptx = outline_to_pptx(cur, deck_title=fn, template_path=template_arg())
            if pptx:
                dc[2].download_button("개요 PPTX", pptx, file_name=fn + ".pptx", mime=PPTX_MIME,
                                      key=f"pptx_{doc_key}", use_container_width=True)
            n_slides = len(re.findall(r"(?m)^\s*#{2,3}\s*슬라이드", cur))
            st.caption(f"슬라이드 {n_slides}장 · {len(cur):,}자  ·  목표 약 {session_hours() * SLIDES_PER_HOUR}장({session_hours()}시간)")
        else:
            st.caption(f"교재 {len(cur):,}자 · 약 {len(cur) / 1800:.1f}쪽(A4)  ·  참고 목표 7쪽↑")
    return st.empty(), st.container()


def script_idle_body(ph, ctrl, md_key, msgs_key, doc_key, hint):
    """생성물 표시 + 수정/정렬점검/직접편집 컨트롤(교재·슬라이드 공용)."""
    if ss[md_key]:
        ph.markdown(ss[md_key])
        with ctrl:
            rc = st.columns([4, 1, 1.3])
            req = rc[0].text_input("수정", key=f"refine_{doc_key}", label_visibility="collapsed",
                                   placeholder="수정 요청 — 예: 예시를 더 추가해줘 / 분량을 줄여줘")
            if rc[1].button("수정", key=f"refbtn_{doc_key}", use_container_width=True):
                if req.strip() and ensure_ready():
                    ss[msgs_key].append({"role": "user", "content": REFINE_TMPL.format(req=req)})
                    ss._pending = {"kind": "refine", "doc": doc_key}
                    st.rerun()
            if rc[2].button("정렬 점검", key=f"chk_{doc_key}", use_container_width=True):
                if ensure_ready():
                    ss._pending = {"kind": "check", "doc": doc_key}
                    st.rerun()
            with st.expander("직접 편집 (마크다운)"):
                _ed = st.text_area("직접 편집", value=ss[md_key], height=380,
                                   key=f"edit_{doc_key}", label_visibility="collapsed")
                if st.button("편집 저장", key=f"savedit_{doc_key}", use_container_width=True):
                    ss[md_key] = _ed
                    ss[msgs_key] = [
                        {"role": "user", "content": "현재 문서(직접 편집본)를 기준으로 이어서 작업합니다."},
                        {"role": "assistant", "content": _ed},
                    ]
                    persist()
                    st.success("편집 내용을 저장했습니다.")
                    st.rerun()
    else:
        ph.info(hint)


def render_syllabus_panel() -> None:
    """강의계획서 출력 패널(다운로드·차트·스트리밍·수정·직접편집). STEP1/2 공용."""
    with st.container(border=True):
        hc = st.columns([3, 1.1, 1.5])
        hc[0].markdown(f'<div class="ida-panel-title">{ICON_DOC}강의계획서</div>', unsafe_allow_html=True)
        if ss.syllabus_md:
            hc[1].download_button("MD", ss.syllabus_md, file_name=out_name("syllabus") + ".md",
                                  mime="text/markdown", use_container_width=True, key="dl_syl_md")
            hc[2].download_button("DOC 저장", md_to_doc_bytes(ss.syllabus_md),
                                  file_name=out_name("syllabus") + ".doc",
                                  mime="application/msword", use_container_width=True, key="dl_syl_doc")
        if ss.syllabus_md:
            st.caption(f"분량 {len(ss.syllabus_md):,}자")
        if ss.syllabus_md and not pending:
            _chart = bloom_chart_html(bloom_counts(ss.syllabus_md))
            if _chart:
                st.markdown(_chart, unsafe_allow_html=True)

        out_ph = st.empty()
        if pending and pending.get("doc") == "syllabus":
            _m = "수정 반영 중…" if pending["kind"] == "refine" else (
                "정렬 점검 중… (Bloom 분포 · 목표–평가 정렬)" if pending["kind"] == "check"
                else "강의계획서 작성 중… (목표 설계 → 주차 분해 → 정렬 매트릭스)")
            with st.spinner(_m):
                run_pending(pending, out_ph)
            persist()
            st.rerun()
        elif ss.syllabus_md:
            out_ph.markdown(ss.syllabus_md)
        else:
            out_ph.info("좌측 사이드바 '강의 기본 정보'를 입력하고 강의계획서를 생성하세요.")

        if ss.syllabus_md and not pending:
            st.divider()
            rc = st.columns([4, 1])
            req = rc[0].text_input("수정 요청", key="refine_syllabus", label_visibility="collapsed",
                                   placeholder="수정 요청 — 예: 7주차 목표를 '분석' 수준으로 높여줘")
            if rc[1].button("수정 요청", key="refbtn_syllabus", use_container_width=True):
                if req.strip() and ensure_ready():
                    ss.syllabus_msgs.append({"role": "user", "content": REFINE_TMPL.format(req=req)})
                    ss._pending = {"kind": "refine", "doc": "syllabus"}
                    st.rerun()
            with st.expander("직접 편집 (마크다운)"):
                _ed = st.text_area("강의계획서 직접 편집", value=ss.syllabus_md, height=420,
                                   key="edit_syllabus", label_visibility="collapsed")
                if st.button("편집 저장", key="savedit_syllabus", use_container_width=True):
                    ss.syllabus_md = _ed
                    ss.syllabus_msgs = [
                        {"role": "user", "content": "현재 강의계획서(직접 편집본)를 기준으로 이어서 작업합니다."},
                        {"role": "assistant", "content": _ed},
                    ]
                    persist()
                    st.success("편집 내용을 저장했습니다.")
                    st.rerun()


# ---------------------------------------------------------------------------
# 사이드바 — 강의 프로젝트 · 강의 기본 정보 · 연결 설정
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f'<div class="ida-panel-title">{ICON_DOC}강의 프로젝트</div>', unsafe_allow_html=True)
    _projects = db.list_projects()
    _labels = ["＋ 새 프로젝트"] + [f'{p["name"]} · {p["updated_at"][5:16]}' for p in _projects]
    _ids = [None] + [p["id"] for p in _projects]
    _cur = _ids.index(ss.project_id) if ss.project_id in _ids else 0
    _sel = st.selectbox("프로젝트 열기", range(len(_labels)), index=_cur,
                        format_func=lambda i: _labels[i], label_visibility="collapsed")
    if _ids[_sel] != ss.project_id:
        if _ids[_sel] is None:
            clear_artifacts()
            ss.project_id = None
        else:
            load_project_into_session(_ids[_sel])
        st.rerun()

    if ss.project_id is None:
        _nm = st.text_input("새 프로젝트 이름", value="", placeholder="예: 교육방법 및 교육공학")
        if st.button("새로 만들기", use_container_width=True, type="primary"):
            clear_artifacts()
            ss.project_id = db.create_project(_nm.strip() or "새 강의")
            st.rerun()
    else:
        _p = next((p for p in _projects if p["id"] == ss.project_id), None)
        st.caption(f"현재 프로젝트: {_p['name'] if _p else '(저장 전)'}")
        with st.expander("이름 변경 · 삭제"):
            _rn = st.text_input("새 이름", value=(_p["name"] if _p else ""), key="rename_input")
            rc1, rc2 = st.columns(2)
            if rc1.button("이름 저장", use_container_width=True):
                db.rename_project(ss.project_id, _rn.strip() or "새 강의")
                st.rerun()
            if rc2.button("삭제", use_container_width=True):
                db.delete_project(ss.project_id)
                ss.project_id = None
                clear_artifacts()
                st.rerun()
    st.divider()

    # ── 강의 기본 정보 (입력) — 2열 배치 ──
    with st.expander("강의 기본 정보", expanded=not ss.syllabus_md):
        with st.form("lecture_form"):
            fc = st.columns(2)
            f_title = fc[0].text_input("과목명 *", value=ss.form.get("title", ""), placeholder="예: 교육공학의 이해")
            f_field = fc[1].text_input("학문 분야", value=ss.form.get("field", ""), placeholder="예: 교육학")
            fc = st.columns(2)
            f_target = fc[0].text_input("수강 대상 *", value=ss.form.get("target", ""), placeholder="예: 학부 2학년")
            f_credit = fc[1].text_input("학점 / 시수", value=ss.form.get("credit", ""), placeholder="예: 3학점, 주 3시간")
            fc = st.columns(2)
            f_weeks = fc[0].selectbox("총 주차", WEEK_CHOICES,
                                      index=WEEK_CHOICES.index(ss.form.get("weeks", 15))
                                      if ss.form.get("weeks", 15) in WEEK_CHOICES else 3)
            f_mode = fc[1].selectbox("강의 방식", MODE_CHOICES,
                                     index=MODE_CHOICES.index(ss.form.get("mode", "대면"))
                                     if ss.form.get("mode", "대면") in MODE_CHOICES else 0)
            f_hours = st.number_input(f"차시 수업 시간(시간) — 슬라이드는 시간당 약 {SLIDES_PER_HOUR}장",
                                      min_value=1, max_value=6, step=1,
                                      value=int(ss.form.get("hours", 2) or 2))
            f_topics = st.text_area("주요 내용 · 주제 *", value=ss.form.get("topics", ""),
                                    placeholder="예: 교수설계 이론, ADDIE 모형, 학습목표 설계, 매체 활용 등")
            fc = st.columns(2)
            f_learner = fc[0].text_input("수강생 특성", value=ss.form.get("learner", ""),
                                         placeholder="예: 전공 기초 이수, 일부 현직 교사")
            f_policy = fc[1].text_input("평가 선호·수업 철학", value=ss.form.get("policy", ""),
                                        placeholder="예: 과정 중심 40%, 토론 중심")
            submitted = st.form_submit_button("강의계획서 생성 →", type="primary", use_container_width=True)
        if submitted:
            if not f_title.strip() or not f_topics.strip():
                st.warning("과목명과 주요 내용은 필수입니다.")
            elif ensure_ready():
                ss.form = dict(title=f_title, field=f_field, target=f_target, credit=f_credit,
                               weeks=f_weeks, mode=f_mode, hours=f_hours,
                               topics=f_topics, learner=f_learner, policy=f_policy)
                ss.syllabus_msgs = [{"role": "user", "content": syllabus_user_msg(ss.form)}]
                ss.step = 2
                ss._pending = {"kind": "gen", "doc": "syllabus"}
                st.rerun()

    # ── 연결 설정 (ChatGPT 계정 OAuth · 구독) ──
    _auth = oauth.status()
    _logged = _auth["logged_in"]
    with st.expander(f"연결 설정 — {'로그인됨 ✓' if _logged else 'ChatGPT 로그인 필요'}",
                     expanded=not ss.had_login):
        s = ss.settings
        if _logged:
            who = _auth.get("email") or _auth.get("account_id") or "계정"
            st.success(f"ChatGPT 로그인됨 · {who}")
            if st.button("로그아웃", use_container_width=True):
                oauth.logout()
                ss.had_login = False
                ss.ping_status = None
                st.rerun()
        else:
            st.caption("ChatGPT(Plus/Pro) 구독 계정으로 로그인합니다. 버튼을 누르면 브라우저가 "
                       "열리고, 로그인하면 자동으로 연결됩니다(사내 API 키 불필요).")
            if st.button("ChatGPT 로그인 →", use_container_width=True, type="primary"):
                with st.spinner("브라우저에서 로그인하세요… (완료 시 자동 연결)"):
                    ok, msg = oauth.login()
                ss.had_login = ok
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

        # 모델 선택 (구독에서 사용할 ChatGPT 모델 슬러그)
        if st.button("모델 목록 불러오기 (계정 기준)", use_container_width=True, disabled=not _logged,
                     help="로그인된 계정에서 실제 사용 가능한 모델 슬러그를 백엔드에서 조회해 목록을 채웁니다."):
            with st.spinner("모델 목록 조회 중…"):
                ss.model_options = llm_mod.list_models()
            if not ss.model_options:
                st.warning("목록을 가져오지 못했습니다. '직접 입력…'으로 슬러그를 넣어보세요.")
            st.rerun()
        # 불러온 목록이 있으면 그걸, 없으면 기본 후보를 사용
        _opts = list(ss.model_options) if ss.model_options else list(settings_mod.MODELS.keys())
        _custom = "직접 입력…"
        _idx = _opts.index(s.model) if s.model in _opts else len(_opts)
        _pick = st.selectbox("사용 모델", _opts + [_custom],
                             index=min(_idx, len(_opts)),
                             format_func=lambda m: settings_mod.MODELS.get(m, m))
        if _pick == _custom:
            s.model = st.text_input("모델 슬러그 직접 입력", value=s.model,
                                    help="예: gpt-5.5, gpt-5.4, gpt-5.4-mini 등 계정에서 노출되는 슬러그")
        else:
            s.model = _pick
        s.effort = st.selectbox("추론 강도(effort)", list(settings_mod.EFFORTS),
                                index=list(settings_mod.EFFORTS).index(s.effort)
                                if s.effort in settings_mod.EFFORTS else 1,
                                help="gpt-5 계열의 사고 강도. 개요·비주얼 원고는 medium, 빠르게는 low.")
        s.unsplash_key = st.text_input("Unsplash Access Key (선택)", value=s.unsplash_key,
                                       type="password",
                                       help="넣으면 디자인 슬라이드 사진을 Unsplash(고품질)에서 가져옵니다. "
                                            "비우면 Openverse(무료 CC)로 동작. unsplash.com/developers 에서 무료 발급.")
        bc1, bc2 = st.columns(2)
        if bc1.button("연결 테스트", use_container_width=True, disabled=not _logged):
            with st.spinner("확인 중…"):
                ss.ping_status = llm_mod.build_provider(s).ping()
        if bc2.button("저장", use_container_width=True, type="primary"):
            settings_mod.save(s)
            st.success("설정을 저장했습니다.")
            st.rerun()
        if ss.ping_status:
            ok, msg = ss.ping_status
            (st.success if ok else st.error)(msg)

    st.caption("산출물은 자동 저장됩니다 (data/app.db · 로컬, GitHub 미포함).")


# ---------------------------------------------------------------------------
# 헤더
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="ida-header">'
    '<div class="ida-eyebrow">AI · 교수설계 스튜디오</div>'
    '<div class="ida-title">교수설계 가이드 에이전트</div>'
    '<div class="ida-sub">ABCD 학습목표 · Bloom 정렬 · 백워드 설계(WHERETO) · Mayer 멀티미디어 원리 기반</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# STEP 바
# ---------------------------------------------------------------------------
sb = st.columns(len(STEP_META))
for idx, (n, tit, desc) in enumerate(STEP_META):
    with sb[idx]:
        active = ss.step == n
        if st.button(f"{n}   {tit}", key=f"stepbtn{n}", use_container_width=True,
                     type="primary" if active else "secondary"):
            ss.step = n
            st.rerun()
        st.caption(desc)

# 좌측 버튼이 예약한 작업 (생성/수정/점검) — 우측에서 소비
pending = ss.get("_pending")
if "_pending" in ss:
    del ss["_pending"]

st.write("")

# ===========================================================================
# STEP 3 — 교재(학생용 읽기 자료)
# ===========================================================================
if ss.step == 3:
    with st.container(border=True):
        st.markdown(f'<div class="ida-panel-title">{ICON_DOC}교재 생성 · STEP 3</div>', unsafe_allow_html=True)
        if not ss.syllabus_md:
            st.info("교재는 강의계획서의 주차 목표를 상속합니다. 먼저 STEP 1~2에서 강의계획서를 생성하세요.")
        else:
            st.caption("선택한 주차의 **학생용 교재(읽기 자료)** 를 생성합니다. 슬라이드는 STEP 4에서 만듭니다.")
            n_weeks = int(ss.form.get("weeks", 15))
            week_opts = list(range(1, n_weeks + 1))
            cc = st.columns([1.3, 3.4, 1.9])
            ss.script_week = cc[0].selectbox("대상 주차", week_opts,
                                             index=week_opts.index(ss.script_week)
                                             if ss.script_week in week_opts else 0,
                                             format_func=lambda w: f"{w}주차", key="wk_doc")
            note = cc[1].text_input("해당 차시 요청사항 (선택)", key="note_doc",
                                    placeholder="예: 사례 중심으로, 표·그림 제안 포함 등")
            cc[2].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if cc[2].button("교재 생성 →", type="primary", use_container_width=True,
                            disabled=bool(pending)):
                if ensure_ready():
                    ss.script_doc_msgs = [{"role": "user",
                                           "content": script_user_msg(ss.script_week, "doc", note, ss.syllabus_md)}]
                    ss._pending = {"kind": "gen", "doc": "script_doc"}
                    st.rerun()
            if st.button("슬라이드 만들기 (STEP 4) →", key="goto4", use_container_width=True):
                ss.step = 4
                st.rerun()

    if ss.syllabus_md:
        doc_ph, doc_ctrl = script_downloads("script_doc_md", "script_doc", False, busy=bool(pending))
        if pending and pending.get("doc") == "script_doc":
            _m = {"gen": "교재 작성 중…", "refine": "수정 반영 중…",
                  "check": "정렬 점검 중…"}.get(pending["kind"], "작성 중…")
            with st.spinner(_m):
                run_pending(pending, doc_ph)
            persist()
            st.rerun()
        else:
            script_idle_body(doc_ph, doc_ctrl, "script_doc_md", "script_doc_msgs", "script_doc",
                             "위 '교재 생성'을 누르면 교재가 여기에 표시됩니다.")

# ===========================================================================
# STEP 4 — 슬라이드(개요 → 이미지·레이아웃 정리)
# ===========================================================================
elif ss.step == 4:
    with st.container(border=True):
        st.markdown(f'<div class="ida-panel-title">{ICON_SLIDE}슬라이드 개요(원고) · STEP 4</div>', unsafe_allow_html=True)
        if not ss.syllabus_md:
            st.info("슬라이드는 강의계획서의 주차 목표를 상속합니다. 먼저 STEP 1~2에서 강의계획서를 생성하세요.")
        else:
            st.caption("차시 슬라이드 **개요(원고)** 를 생성합니다. 이후 **5단계** 노트북LM 렌더 코드, "
                       "**6단계** 비주얼 원고·디자인 PPTX 로 이어집니다.")
            n_weeks = int(ss.form.get("weeks", 15))
            week_opts = list(range(1, n_weeks + 1))
            cc = st.columns([1.3, 3.4, 1.9])
            ss.script_week = cc[0].selectbox("대상 주차", week_opts,
                                             index=week_opts.index(ss.script_week)
                                             if ss.script_week in week_opts else 0,
                                             format_func=lambda w: f"{w}주차", key="wk_ppt")
            note = cc[1].text_input("해당 차시 요청사항 (선택)", key="note_ppt",
                                    placeholder="예: 오리엔테이션 최소화, 개념마다 예시 등")
            cc[2].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if cc[2].button("① 슬라이드 개요 생성 →", type="primary", use_container_width=True,
                            disabled=bool(pending)):
                if ensure_ready():
                    ss.script_ppt_msgs = [{"role": "user",
                                           "content": script_user_msg(ss.script_week, "ppt", note, ss.syllabus_md)}]
                    ss._pending = {"kind": "gen", "doc": "script_ppt"}
                    st.rerun()
            if ss.script_ppt_md.strip():
                nav = st.columns(2)
                if nav[0].button("5단계 · 노트북LM 렌더 코드 →", use_container_width=True):
                    ss.step = 5
                    st.rerun()
                if nav[1].button("6단계 · 비주얼 원고 · 디자인 PPTX →", use_container_width=True):
                    ss.step = 6
                    st.rerun()

    if ss.syllabus_md:
        ppt_ph, ppt_ctrl = script_downloads("script_ppt_md", "script_ppt", True, busy=bool(pending))
        if pending and pending.get("doc") == "script_ppt" and pending.get("kind") in ("gen", "refine", "check"):
            _m = {"gen": "슬라이드 개요 작성 중…", "refine": "수정 반영 중…",
                  "check": "정렬 점검 중…"}.get(pending["kind"], "작성 중…")
            with st.spinner(_m):
                run_pending(pending, ppt_ph)
            persist()
            st.rerun()
        else:
            script_idle_body(ppt_ph, ppt_ctrl, "script_ppt_md", "script_ppt_msgs", "script_ppt",
                             "위 '① 슬라이드 개요 생성'을 누르면 개요가 여기에 표시됩니다.")

# ===========================================================================
# STEP 5 — 노트북LM 렌더 코드
# ===========================================================================
elif ss.step == 5:
    with st.container(border=True):
        st.markdown(f'<div class="ida-panel-title">{ICON_SLIDE}노트북LM 렌더 코드 · STEP 5</div>', unsafe_allow_html=True)
        if not ss.script_ppt_md.strip():
            st.info("먼저 4단계에서 슬라이드 개요(원고)를 생성하세요.")
        else:
            st.caption("① 개요(원고)를 NotebookLM 소스로 붙여넣고 → ② 아래 **렌더 코드**를 NotebookLM 채팅에 "
                       "붙여넣어 슬라이드를 생성합니다.")
            _detected = slide_render.count_slides(ss.script_ppt_md)
            r2 = st.columns([1.2, 1.2, 2.6, 1.8])
            ss.render_total = r2[0].number_input("총 슬라이드", min_value=0, max_value=200, step=1,
                                                 value=int(ss.render_total or _detected),
                                                 help="0이면 개요에서 자동 감지. 보통 2시간=40장.")
            ss.render_per_chunk = r2[1].number_input("한 번에(청크)", min_value=5, max_value=60, step=5,
                                                     value=int(ss.render_per_chunk or 20),
                                                     help="한 배치가 생성할 장수. 40장÷20 = 배치 2개.")
            _dkeys = list(slide_render.DESIGN_SYSTEMS.keys())
            ss.render_design = r2[2].selectbox("디자인 시스템", _dkeys,
                                               index=_dkeys.index(ss.render_design)
                                               if ss.render_design in _dkeys else 0,
                                               format_func=lambda k: slide_render.DESIGN_SYSTEMS[k]["label"])
            _ikeys = list(slide_render.INTENSITIES.keys())
            ss.render_intensity = r2[3].selectbox("스타일 강도", _ikeys,
                                                  index=_ikeys.index(ss.render_intensity)
                                                  if ss.render_intensity in _ikeys else 1,
                                                  format_func=lambda k: slide_render.INTENSITIES[k]["label"])
            r2b = st.columns([3.4, 3.4])
            _fkeys = list(slide_render.FORMATS.keys())
            ss.render_format = r2b[0].selectbox("출력 형식", _fkeys,
                                                index=_fkeys.index(ss.render_format)
                                                if ss.render_format in _fkeys else 0,
                                                format_func=lambda k: slide_render.FORMATS[k],
                                                help="NotebookLM 이 커널 오버라이드 문구를 거부하면 BATCH(자연어)를 쓰세요.")
            ss.render_pagenum = r2b[1].checkbox("페이지 번호 지시 포함", value=bool(ss.render_pagenum),
                                                help="각 슬라이드 하단에 연속 페이지 번호를 넣도록 지시(생성기가 무시할 수 있음).")
            gr = st.columns([2.6, 2.6, 3.0])
            if gr[0].button("렌더 코드 생성", type="primary", use_container_width=True,
                            disabled=(not ss.script_ppt_md.strip() and not ss.render_total)):
                if not run_render_code():
                    st.warning("먼저 4단계 개요를 생성하거나 ‘총 슬라이드’ 수를 입력하세요.")
                else:
                    st.rerun()
            if ss.render_code:  # 다운로드는 상단에(스크롤 하단 X)
                gr[1].download_button("⬇ 렌더 코드 (.txt)", ss.render_code.encode("utf-8"),
                                      file_name=(ss.deck_name or out_name("슬라이드")) + "_노트북LM_렌더코드.txt",
                                      mime="text/plain", key="dl_rendercode", use_container_width=True)

    if ss.script_ppt_md.strip():
        with st.expander("📋 슬라이드 개요(원고) 전체 복사 — NotebookLM 소스용",
                         expanded=not bool(ss.render_code)):
            st.caption("코드블록 **우상단 복사 아이콘**으로 전체 복사 → NotebookLM ‘소스 추가 → 복사한 텍스트 "
                       "붙여넣기’. 또는 4단계에서 MD 파일을 내려받아 소스에 드래그.")
            st.code(ss.script_ppt_md, language="markdown")
        if ss.render_code:
            with st.expander("노트북LM 렌더 코드 — NotebookLM 채팅에 붙여넣기", expanded=True):
                st.caption("아래 코드를 NotebookLM 채팅에 붙여넣으면 슬라이드가 배치별로 생성됩니다. "
                           "코드블록 우상단 아이콘으로 전체 복사.")
                st.code(ss.render_code, language="text")

# ===========================================================================
# STEP 6 — 비주얼 원고 · 디자인 PPTX (SME 가 여기에 NotebookLM 슬라이드를 합침)
# ===========================================================================
elif ss.step == 6:
    with st.container(border=True):
        st.markdown(f'<div class="ida-panel-title">{ICON_SLIDE}비주얼 원고 · 디자인 PPTX · STEP 6</div>', unsafe_allow_html=True)
        if not ss.script_ppt_md.strip():
            st.info("먼저 4단계에서 슬라이드 개요(원고)를 생성하세요.")
        else:
            st.caption("**비주얼 원고**(사진 갈음 아트디렉션)와 **디자인 PPTX**(사진 좌·우 배치)를 만듭니다. "
                       "이 **최종 PPTX** 를 내려받아 5단계(NotebookLM) 슬라이드를 SME 가 합칩니다.")
            _has_outline = bool(ss.script_ppt_md.strip())
            bc = st.columns([2.8, 2.8, 2.2])
            if bc[0].button("① 비주얼 원고 생성 (사진 갈음)", type="primary",
                            disabled=bool(pending), use_container_width=True):
                if ensure_ready():
                    ss._pending = {"kind": "visualbrief", "doc": "script_ppt"}
                    st.rerun()
            if bc[1].button("② 이미지·레이아웃 정리 (디자인 PPTX)", type="primary",
                            disabled=(not _has_outline) or bool(pending), use_container_width=True):
                if ensure_ready():
                    ss._pending = {"kind": "design", "doc": "script_ppt"}
                    st.rerun()
            # 다운로드는 상단에(완료 시 첫 산출물 위)
            if ss.deck_bytes or ss.visual_brief_md:
                dl = st.columns(3)
                if ss.deck_bytes:
                    dl[0].download_button("⬇ 디자인 PPTX (최종)", ss.deck_bytes,
                                          file_name=(ss.deck_name or out_name("슬라이드")) + ".pptx",
                                          mime=PPTX_MIME, key="dl_deck", use_container_width=True)
                    dl[1].download_button("⬇ 이미지 출처(.txt)", ss.credits_txt.encode("utf-8"),
                                          file_name=(ss.deck_name or "슬라이드") + "_이미지출처.txt",
                                          mime="text/plain", key="dl_credits", use_container_width=True)
                if ss.visual_brief_md:
                    dl[2].download_button("⬇ 비주얼 원고 (.md)", ss.visual_brief_md,
                                          file_name=(ss.deck_name or out_name("슬라이드")) + "_비주얼원고.md",
                                          mime="text/markdown", key="dl_vbrief", use_container_width=True)

            _tpl_on = TEMPLATE_PATH.exists()
            with st.expander(f"PPT 회사 양식(.pptx) — {'적용됨 ✓' if _tpl_on else '기본 양식 사용 중'}"):
                st.caption("회사 양식 .pptx 를 올리면 디자인 슬라이드가 그 마스터·로고를 상속합니다. "
                           "(또는 assets/logo.png 를 두면 우상단 자동 삽입) 양식 파일은 로컬 assets/ 에만 저장됩니다.")
                up = st.file_uploader("회사 양식 업로드 (.pptx / .potx)", type=["pptx", "potx"], key="tpl_up")
                if up is not None:
                    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                    TEMPLATE_PATH.write_bytes(up.getvalue())
                    st.success("회사 양식이 적용되었습니다.")
                if _tpl_on and st.button("양식 제거(기본으로 되돌리기)", key="tpl_rm"):
                    TEMPLATE_PATH.unlink(missing_ok=True)
                    st.rerun()

    if ss.script_ppt_md.strip():
        vb_ph = st.empty()
        if pending and pending.get("kind") == "design":
            status = st.empty()
            with st.spinner("이미지·레이아웃 정리 중… (구성 분석 → 사진 수집 → 빌드)"):
                run_design(status)
            st.rerun()
        elif pending and pending.get("kind") == "visualbrief":
            with st.spinner("비주얼 원고 생성 중… (슬라이드별 아트디렉션)"):
                run_visual_brief(vb_ph)
            persist()
            st.rerun()
        elif ss.visual_brief_md:
            with st.expander("비주얼 원고 (사진 갈음 아트디렉션)", expanded=True):
                st.markdown(ss.visual_brief_md)
                _ed = st.text_area("직접 편집", value=ss.visual_brief_md, height=260,
                                   key="edit_vbrief", label_visibility="collapsed")
                if st.button("비주얼 원고 편집 저장", key="save_vbrief", use_container_width=True):
                    ss.visual_brief_md = _ed
                    st.success("저장했습니다. (② 디자인 PPTX 사진 검색에 반영)")
                    st.rerun()
        else:
            st.info("‘① 비주얼 원고 생성’ 또는 ‘② 디자인 PPTX’ 를 누르면 결과가 여기에 표시됩니다.")

# ===========================================================================
# STEP 1 — 강의계획서 전체 폭 (입력은 사이드바)
# ===========================================================================
elif ss.step == 1:
    render_syllabus_panel()

# ===========================================================================
# STEP 2 — 상단 컨트롤 + 전체 폭 강의계획서
# ===========================================================================
else:
    with st.container(border=True):
        st.markdown(f'<div class="ida-panel-title">{ICON_INFO}강의계획서 점검 · STEP 2</div>', unsafe_allow_html=True)
        st.caption("① 정렬 점검: 강의계획서가 실무형 기준을 지켰는지 AI가 검토해 수정 제안을 문서 하단에 덧붙입니다.")
        _checked = "정렬 점검 보고" in (ss.syllabus_md or "")  # 점검 완료 시 강조를 ②로 이동
        _busy = bool(pending)  # 생성/점검/수정 진행 중이면 버튼 비활성화
        bc = st.columns([1.8, 2.6, 3.2])
        if bc[0].button("① 정렬 점검 실행", use_container_width=True,
                        type=("secondary" if _checked else "primary"),
                        disabled=_busy or not ss.syllabus_md):
            if ss.syllabus_md and ensure_ready():
                ss._pending = {"kind": "check", "doc": "syllabus"}
                st.rerun()
            elif not ss.syllabus_md:
                st.warning("먼저 강의계획서를 생성하세요.")
        if bc[1].button("② 교재·슬라이드 작성으로 이동 →", use_container_width=True,
                        type=("primary" if _checked else "secondary"),
                        disabled=_busy or not ss.syllabus_md):
            ss.step = 3
            st.rerun()
    render_syllabus_panel()
