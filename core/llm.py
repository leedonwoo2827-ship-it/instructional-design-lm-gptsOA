# -*- coding: utf-8 -*-
"""LLM provider — ChatGPT 계정 OAuth(구독) · Responses API.

사내 LiteLLM 프록시를 제거하고, 사용자의 ChatGPT(Plus/Pro) 구독 계정으로 로그인해
ChatGPT 백엔드 Responses API(chatgpt.com/backend-api/wham)를 호출한다. openai SDK 의
`responses.create` 를 커스텀 base_url + `ChatGPT-Account-Id` 헤더로 사용하며, 토큰은
core/oauth.py 가 관리(만료 임박 시 선제 갱신, 401 시 재갱신+재시도).

인터페이스는 기존과 동일: stream() / generate() / ping() / build_provider(settings).
chat 스타일 messages([{role,content}])를 Responses 의 instructions + input 으로 변환한다.
gpt-5 계열은 temperature 를 받지 않으므로 보내지 않는다(reasoning.effort 로 제어).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List

from core import oauth
from core.user_settings import Settings


def _to_responses_input(messages: List[Dict]) -> List[Dict]:
    """chat messages → Responses API input 아이템(assistant 는 output_text)."""
    items = []
    for m in messages:
        role = m.get("role", "user")
        if role == "system":
            continue  # system 은 instructions 로 별도 전달
        ctype = "output_text" if role == "assistant" else "input_text"
        items.append({
            "role": role,
            "content": [{"type": ctype, "text": str(m.get("content", ""))}],
        })
    return items


@dataclass
class ChatGPTOAuthProvider:
    model: str
    effort: str = "medium"          # gpt-5 reasoning effort: low|medium|high
    _retried: bool = field(default=False, repr=False)

    def _client(self):
        from openai import OpenAI  # lazy import
        creds = oauth.get_access()
        if not creds or not creds[0]:
            raise RuntimeError("ChatGPT 로그인이 필요합니다. 사이드바에서 'ChatGPT 로그인'을 눌러 연결하세요.")
        access, account_id = creds
        headers = {"User-Agent": "instructional-design-agent/0.2"}
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id
        return OpenAI(api_key=access, base_url=oauth.BACKEND_BASE_URL, default_headers=headers)

    def _body(self, system: str, messages: List[Dict], *, max_tokens: int) -> dict:
        # 이 백엔드(Codex/wham) 제약:
        #  · stream=True 강제(비스트리밍은 400 'Stream must be set to true')
        #  · max_output_tokens 미지원(400 'Unsupported parameter') → 보내지 않는다
        body = dict(
            model=self.model,
            instructions=system or "You are a helpful assistant.",
            input=_to_responses_input(messages),
            store=False,
            stream=True,
        )
        if self.model.startswith("gpt-5"):
            body["reasoning"] = {"effort": self.effort, "summary": "auto"}
        return body

    def _is_auth_error(self, e: Exception) -> bool:
        code = getattr(e, "status_code", None)
        return code == 401 or "401" in str(e) or e.__class__.__name__ == "AuthenticationError"

    def stream(self, system: str, messages: List[Dict], *, max_tokens: int = 10000,
               temperature: float = 0.7) -> Iterator[str]:  # temperature 미사용(구독 모델)
        try:
            events = self._client().responses.create(
                **self._body(system, messages, max_tokens=max_tokens))
            for ev in events:
                if getattr(ev, "type", "") == "response.output_text.delta":
                    delta = getattr(ev, "delta", "")
                    if delta:
                        yield delta
            self._retried = False
        except Exception as e:  # noqa: BLE001
            if self._is_auth_error(e) and not self._retried and oauth.refresh():
                self._retried = True
                yield from self.stream(system, messages, max_tokens=max_tokens)
                return
            raise

    def generate(self, system: str, messages: List[Dict], *, max_tokens: int = 10000,
                 temperature: float = 0.7) -> str:
        # 백엔드가 스트리밍만 허용하므로, 스트림을 소비해 하나의 문자열로 합친다.
        return "".join(self.stream(system, messages, max_tokens=max_tokens))

    def ping(self) -> tuple[bool, str]:
        try:
            text = self.generate(
                "You are a connection tester.",
                [{"role": "user", "content": "Respond with exactly: OK"}],
                max_tokens=16,
            )
            return True, f"OK ({self.model}) → {text.strip()[:40]}"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"


def build_provider(settings: Settings) -> ChatGPTOAuthProvider:
    return ChatGPTOAuthProvider(model=settings.model, effort=getattr(settings, "effort", "medium"))


def list_models() -> list[str]:
    """로그인된 계정에서 사용 가능한 모델 슬러그 목록을 백엔드에서 조회.

    계정마다 허용 모델이 다르므로(예: 'gpt-5.1' 미지원 계정), 실제 목록을 받아
    사이드바 드롭다운을 채운다. 실패 시 빈 리스트.
    """
    import requests  # noqa: PLC0415
    creds = oauth.get_access()
    if not creds or not creds[0]:
        return []
    access, account_id = creds
    headers = {"Authorization": f"Bearer {access}",
               "User-Agent": "instructional-design-agent/0.2"}
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id

    slugs: list[str] = []
    for url in (f"{oauth.BACKEND_BASE_URL}/models",
                f"{oauth.BACKEND_BASE_URL}/models?client_version=0.0.0"):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            j = r.json() or {}
            items = j.get("models") or j.get("data") or []
            for it in items:
                s = (it.get("slug") or it.get("id") or "").strip() if isinstance(it, dict) else str(it).strip()
                if s:
                    slugs.append(s)
            if slugs:
                break
        except Exception as e:  # noqa: BLE001
            print(f"[models] 조회 오류({url}): {e}", flush=True)
            continue

    seen, out = set(), []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
