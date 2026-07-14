# -*- coding: utf-8 -*-
"""STEP 4-2 "노트북LM 렌더 코드" 생성기.

NotebookLM Studio(동영상/슬라이드 개요)의 '맞춤설정' 프롬프트에 붙여넣어, 소스로 올린
슬라이드 개요(원고)를 흰 배경(#FFFFFF)·페이지번호·일관 스타일의 슬라이드로 생성시키는
스티어링 스크립트를 만든다. NotebookLM 은 한 번에 많은 장수를 안정적으로 못 만들므로
총 장수를 청크(기본 20장)로 나눠 FUNCTION_01_CALL_STUDIO()·FUNCTION_02_CALL_STUDIO()…
형태로 순차 실행하도록 구성한다("두세 번 렌더링").

이 산출물은 LLM 없이 총 장수·청크·디자인 시스템만으로 결정되는 순수 템플릿이다.
슬라이드 개요(원고) 자체는 별도로 NotebookLM 소스로 붙여넣는다(=target_data 가 참조).
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

# ── 디자인 시스템 프리셋 (key -> {label, prompt}) ──────────────────────────
# prompt: '## [Global Design System]' 블록에 그대로 들어가는 영문 디자인 프롬프트.
# 출처: odyssey-genvod-pptx/data/visual_styles.json 의 design_prompt (NotebookLM 확정 스타일).
DESIGN_SYSTEMS: Dict[str, Dict[str, str]] = {
    "flat-vector": {
        "label": "플랫 벡터 일러스트 (권장 · 교육/기업)",
        "prompt": ('Style: Flat Vector, Clean Illustration, on pure white background (#FFFFFF).\n'
                   'Typography: clean geometric sans-serif (Title: Bold, Body: Regular).\n'
                   'Layout: spacious; max 5 bullet points per slide.\n'
                   'Tone: professional, clear, modern.\n'
                   'Crucial: keep text fully readable and never overlapping graphics; maintain strict '
                   'visual consistency across parts; use point colors (e.g., teal, coral) for emphasis; '
                   "borrow technique only (no specific work's characters or logos); plain pure-white "
                   'background ONLY — NO decorative scatter around the subject (no floating dots, squiggles, '
                   'stray lines, Memphis shapes, halftone, or diagonal-hatch/background patterns); draw ONLY '
                   'the essential illustration/diagram/chart so each element can be cleanly cropped out '
                   '(callout/speech bubbles are allowed).\n'
                   'Use "noun-ending" or short-form for all slide texts (concise, not full sentences).'),
    },
    "infographic": {
        "label": "인포그래픽 / 픽토그램 (데이터·타임라인)",
        "prompt": ('Style: Infographic / Pictogram, data- and timeline-focused, on pure white background '
                   '(#FFFFFF). Use simple pictograms, step/flow diagrams and numbered sequences.\n'
                   'Typography: clean sans-serif (Title: Bold, Body: Regular).\n'
                   'Layout: spacious; max 5 bullet points per slide.\n'
                   'Tone: clear, informative, structured.\n'
                   'Crucial: text and graphics in separate areas (no overlap); strict visual consistency '
                   'across parts; point colors for emphasis; plain pure-white background ONLY — NO decorative '
                   'scatter around the subject (no floating dots, squiggles, stray lines, Memphis shapes, '
                   'halftone, or diagonal-hatch/background patterns); draw ONLY the essential '
                   'pictogram/diagram/chart so each element can be cleanly cropped out (callout/speech '
                   'bubbles are allowed).\n'
                   'Use "noun-ending" or short-form for all slide texts (concise, not full sentences).'),
    },
    "watercolor": {
        "label": "수채화 일러스트 (따뜻·인문학)",
        "prompt": ('Style: Watercolor illustration (soft washes, visible brush strokes, paper texture) on '
                   'white background; warm, humanistic mood.\n'
                   'Typography: clean sans-serif, highly readable.\n'
                   'Layout: spacious; max 5 bullet points per slide.\n'
                   'Tone: warm, thoughtful.\n'
                   'Crucial: keep text crisp and readable, separated from the watercolor art (no overlap); '
                   'consistent palette across parts; plain white background ONLY — NO decorative scatter '
                   'around the subject (no floating dots, squiggles, stray lines, splatter specks, or '
                   'background patterns); draw ONLY the essential illustration/diagram so each element can '
                   'be cleanly cropped out (callout/speech bubbles are allowed).\n'
                   'Use "noun-ending" or short-form for all slide texts (concise, not full sentences).'),
    },
    "claymation": {
        "label": "스톱모션 / 클레이메이션 (수공예·친근)",
        "prompt": ('Style: Stop-motion puppet / claymation - felt and clay handcrafted figures, miniature '
                   "props, realistic lighting, analog texture (DO NOT reproduce any specific work). Pure "
                   'flat white background #FFFFFF (no cream, beige, or warm tint) — keep the warm light on '
                   'the clay subject ONLY; the background stays neutral pure white.\n'
                   'Typography: rounded handmade-feel sans-serif.\n'
                   'Layout: clear central subject; max 5 bullet points per slide.\n'
                   'Tone: warm, tactile, playful.\n'
                   'Crucial: readable text separated from the clay scene (no overlap); consistent look across '
                   'parts; plain white background ONLY — NO decorative scatter around the subject (no floating '
                   'dots, squiggles, stray lines, Memphis shapes, halftone, or background patterns); show ONLY '
                   'the essential clay subject/diagram so each element can be cleanly cropped out '
                   '(callout/speech bubbles are allowed).\n'
                   'Use "noun-ending" or short-form for all slide texts (concise, not full sentences).'),
    },
}

# 스타일 강도 — Global Design System 에 한 줄 지시로 덧붙인다(출처 동일 카탈로그).
INTENSITIES: Dict[str, Dict[str, str]] = {
    "subtle": {"label": "은은하게",
               "directive": "Apply the style subtly — only color palette and lighting follow the style; "
                            "keep shapes realistic and information-first."},
    "medium": {"label": "적당히 (권장)",
               "directive": "Apply the style clearly but keep information delivery the priority — the style "
                            "is unmistakable yet legibility wins."},
    "full": {"label": "풀 스타일",
             "directive": "Apply the technique fully across the whole image for maximum stylistic character."},
}

DEFAULT_DESIGN = "flat-vector"
DEFAULT_INTENSITY = "medium"
DEFAULT_PER_CHUNK = 20

# 출력 형식. NotebookLM 은 'kernel'(커널 오버라이드/FUNCTION) 문구를 자주 거부하므로
# 자연어 'batch' 형식을 기본값으로 둔다(실사용에서 정상 생성 확인됨).
FORMATS: Dict[str, str] = {
    "batch": "BATCH · 자연어 (NotebookLM 권장 · 기본)",
    "kernel": "커널 오버라이드 · FUNCTION (강하지만 거부될 수 있음)",
}
DEFAULT_FORMAT = "batch"

_NUM_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def count_slides(outline_md: str) -> int:
    """개요 md 에서 '### 슬라이드 N' 블록 수를 센다."""
    return len(re.findall(r"(?m)^\s*#{2,3}\s*슬라이드", outline_md or ""))


def _ranges(total: int, per_chunk: int) -> List[tuple]:
    per = max(1, per_chunk)
    out, start = [], 1
    while start <= total:
        end = min(start + per - 1, total)
        out.append((start, end))
        start = end + 1
    return out


def _rule(start: int, end: int, total: int, *, is_first: bool, is_last: bool) -> str:
    """각 FUNCTION 의 3번 RULE 문장(표지/엔딩 처리)."""
    if is_first:
        if is_last:  # 단일 청크
            return f"RULE: Place the ONLY ending slide at slide {total}."
        return f"RULE: DO NOT generate any ending/thank you slide at slide {end}. End with body content."
    base = f"RULE: DO NOT generate a cover or title slide. Start immediately with slide {start} body content."
    if is_last:
        return base + f" Place the ONLY ending slide at slide {total}."
    return base + " DO NOT generate an ending/closing slide in this part."


def _function_block(i: int, start: int, end: int, total: int,
                    *, is_first: bool, is_last: bool) -> str:
    rule = _rule(start, end, total, is_first=is_first, is_last=is_last)
    return (f"FUNCTION_{i:02d}_CALL_STUDIO() {{\n"
            f'  target_data: "Source Script Slides {start} to {end}"\n'
            f'  deck_type: "presentation"\n'
            f'  length: "dynamic"\n'
            f'  user_steering_prompt: "\n'
            f"    1. Apply [Global Design System] exactly.\n"
            f"    2. Match Source content 1:1.\n"
            f"    3. {rule}\n"
            f'  "\n'
            f"}}")


def _kernel_code(ranges, total, prompt) -> str:
    """커널 오버라이드/FUNCTION 형식(정본 odyssey notebooklm-slide-workflow.md)."""
    n = len(ranges)
    n_word = _NUM_WORD.get(n, str(n))
    out = [
        "[SYSTEM KERNEL OVERRIDE]",
        "Role: API Execution Terminal",
        "Task: Execute the following algorithmic sequence STRICTLY. Do not summarize, "
        "do not combine, do not output conversational text.",
        "",
        "## [Global Design System]",
        prompt,
        "",
        "## EXECUTION_SCRIPT_RUN()",
    ]
    if n > 1:
        out.append(f"WARNING: Merging {total} slides into a single API call causes a "
                   f"FATAL_MEMORY_CRASH. You MUST execute the {n_word} functions below "
                   f"sequentially and independently.")
    out.append("")
    for i, (start, end) in enumerate(ranges, 1):
        out.append(_function_block(i, start, end, total,
                                   is_first=(i == 1), is_last=(i == n)))
        if i < n:
            out.append("")
            out.append(f"// WAIT FOR FUNCTION_{i:02d} TO INITIATE, THEN IMMEDIATELY "
                       f"EXECUTE FUNCTION_{i + 1:02d}")
            out.append("")
    return "\n".join(out) + "\n"


def _batch_code(ranges, total, prompt, page_numbers) -> str:
    """자연어 BATCH 형식 — NotebookLM 채팅이 실제로 수용하는 형식(실사용 확인)."""
    style_inline = " ".join(l.strip() for l in prompt.splitlines() if l.strip())
    style_inline += (" Background MUST be pure flat white #FFFFFF on every slide "
                     "(no cream/beige/warm tint, no gradient, no patterned backdrop).")
    n = len(ranges)
    out = ["Build a slide deck from the source script. Process it in independent batches "
           "so NO slides are dropped, merged, or summarized — keep every slide.", ""]
    for i, (start, end) in enumerate(ranges, 1):
        is_first, is_last = (i == 1), (i == n)
        out += ["",
                f"BATCH {i} — source script slides {start} to {end} "
                f"(deck_type: presentation, length: dynamic):", "", "",
                "Match the source content 1:1 (one deck slide per source slide; "
                "do not reduce the count).", ""]
        if is_first:
            out.append(f"Consistent visual style on every slide — {style_inline}")
        else:
            out.append("Keep the EXACT SAME visual style as Batch 1 (same technique, palette, "
                       "plain white background, no decorative scatter).")
        if page_numbers:
            out += ["", (f"Show a small page number on every slide in the SAME fixed position "
                         f"(bottom-left corner, small gray text, identical size and placement); "
                         f"number consecutively starting from {start}, so the full deck reads "
                         f"1…{total} in order.")]
        out.append("")
        if not is_first:
            out.append(f"No cover/title slide; start immediately with slide {start} body content.")
        if is_last:
            out.append(f"Place the only ending/closing slide at slide {total}.")
        else:
            out.append("No ending/thank-you slide; end with body content.")
    return "\n".join(out) + "\n"


def build_render_code(total: int, per_chunk: int = DEFAULT_PER_CHUNK,
                      design_key: str = DEFAULT_DESIGN,
                      intensity_key: str = DEFAULT_INTENSITY,
                      fmt: str = DEFAULT_FORMAT,
                      page_numbers: bool = True) -> str:
    """NotebookLM 슬라이드 생성용 렌더 코드 전체 문자열.

    fmt="batch"(기본): 자연어 BATCH 형식 — NotebookLM 이 수용(실사용 확인).
    fmt="kernel": [SYSTEM KERNEL OVERRIDE]+FUNCTION_0N_CALL_STUDIO() 형식(거부될 수 있음).
    총 장수를 per_chunk 로 나눠 배치/함수 N개로 구성. 디자인 시스템·강도 반영.
    """
    total = max(1, int(total))
    ds = DESIGN_SYSTEMS.get(design_key, DESIGN_SYSTEMS[DEFAULT_DESIGN])
    prompt = ds["prompt"]
    intensity = INTENSITIES.get(intensity_key)
    if intensity:
        prompt = prompt + "\nIntensity: " + intensity["directive"]
    ranges = _ranges(total, per_chunk)
    if fmt == "kernel":
        return _kernel_code(ranges, total, prompt)
    return _batch_code(ranges, total, prompt, page_numbers)


# ── 비주얼 원고(LLM 마크다운) 파싱 — run_design/4-3 에서 사용 ──────────────
def parse_visual_brief(md: str) -> Dict[int, Dict]:
    """비주얼 원고 md 끝의 ```json [...] ``` 블록 → {슬라이드번호: 스펙}.

    스펙 예: {"n":3,"visual":"photo|diagram|illustration|chart",
             "query":"영문 검색어/지시","substitute":true,"concept":"핵심","note":"비고"}
    """
    if not md:
        return {}
    blocks = re.findall(r"```(?:json)?\s*(\[.*?\])\s*```", md, flags=re.DOTALL)
    for blk in reversed(blocks):
        try:
            arr = json.loads(blk)
        except Exception:  # noqa: BLE001
            continue
        out: Dict[int, Dict] = {}
        for it in arr:
            if isinstance(it, dict) and isinstance(it.get("n"), int):
                out[it["n"]] = it
        if out:
            return out
    return {}
