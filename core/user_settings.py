# -*- coding: utf-8 -*-
"""GUI-managed settings persisted to data/user_settings.json.

교수설계 가이드 에이전트는 사용자의 ChatGPT(Plus/Pro) 구독 계정으로 로그인해
ChatGPT 백엔드(Responses API)를 사용한다(사내 LiteLLM 프록시 제거). 로그인 토큰은
core/oauth.py 가 data/chatgpt_auth.json 에 관리하며, 여기서는 모델/토큰수/이미지 키
같은 사용자 설정만 저장한다. 저장 파일과 .env, 토큰 파일은 GitHub 에 올리지 않는다.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "user_settings.json"

DEFAULT_MODEL = "gpt-5.5"

# 선택 가능한 ChatGPT 모델 슬러그 (id -> 표시 라벨) — 기본 후보.
# 계정마다 허용 모델이 다르므로(예: 일부 계정은 'gpt-5.1' 미지원), 사이드바 '모델 목록
# 불러오기'로 계정 기준 실제 목록을 받아 채우는 것을 권장한다. 직접 입력도 허용.
MODELS: dict[str, str] = {
    "gpt-5.5": "GPT-5.5 (권장 · 범용)",
    "gpt-5.4": "GPT-5.4",
    "gpt-5.4-mini": "GPT-5.4 mini (빠름)",
}

EFFORTS = ("low", "medium", "high")


@dataclass
class Settings:
    model: str = DEFAULT_MODEL
    # gpt-5 계열 추론 강도(low|medium|high). 디자인/JSON 작업은 low 로 자동 하향.
    effort: str = "medium"
    # 강의계획서/원고는 표가 많은 장문이라 넉넉히
    max_tokens: int = 10000
    temperature: float = 0.7  # 구독 Responses 경로에서는 미사용(호환 위해 유지)
    # 디자인 슬라이드 사진용(선택). 있으면 Unsplash, 없으면 Openverse.
    unsplash_key: str = ""


def _env_defaults() -> Settings:
    s = Settings()
    s.model = os.environ.get("CHATGPT_MODEL", s.model)
    s.effort = os.environ.get("CHATGPT_EFFORT", s.effort)
    s.unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY", s.unsplash_key)
    return s


def load() -> Settings:
    base = _env_defaults()
    if not SETTINGS_PATH.exists():
        return base
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    merged = asdict(base)
    merged.update({k: v for k, v in data.items() if k in merged})
    if merged.get("effort") not in EFFORTS:
        merged["effort"] = "medium"
    return Settings(**merged)


def save(settings: Settings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
