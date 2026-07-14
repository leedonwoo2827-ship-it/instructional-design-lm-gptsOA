# -*- coding: utf-8 -*-
"""ChatGPT 계정 OAuth(구독) 로그인 — Codex CLI "Sign in with ChatGPT" 방식.

브라우저 PKCE 로그인으로 사용자의 ChatGPT(Plus/Pro) 구독 계정에 연결하고,
access_token · refresh_token · account_id 를 data/chatgpt_auth.json 에 저장한다.
이 토큰으로 ChatGPT 백엔드 Responses API(chatgpt.com/backend-api/wham)를 호출하므로
별도 API 종량 과금 없이 구독으로 모델을 사용한다.

값 출처(공개): openai/codex 로그인 플로우 · 7shi/codex-oauth 참고 구현.
  client_id=app_EMoamEEZ73f0CkXaXp7hrann · redirect=localhost:1455 · PKCE(S256).
토큰(민감정보)은 GitHub 에 올리지 않는다(.gitignore 에 data/chatgpt_auth.json 추가).
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional, Tuple

# ── OAuth 상수(Codex 공개 클라이언트) ─────────────────────────────────────
AUTH_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
SCOPE = "openid profile email offline_access"
CALLBACK_PORTS = (1455, 1457)  # Codex 등록 콜백 포트
BACKEND_BASE_URL = "https://chatgpt.com/backend-api/wham"

AUTH_PATH = Path(__file__).resolve().parent.parent / "data" / "chatgpt_auth.json"
_REFRESH_MARGIN_S = 120  # 만료 2분 전 선제 갱신


# ── 저수준 유틸 ────────────────────────────────────────────────────────────
def _requests():
    import requests  # noqa: PLC0415
    return requests


def _pkce() -> Tuple[str, str]:
    """(code_verifier, code_challenge S256)."""
    verifier = secrets.token_urlsafe(96)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _b64url_json(segment: str) -> dict:
    pad = "=" * (-len(segment) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(segment + pad).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _account_id_from_id_token(id_token: str) -> str:
    """id_token(JWT) 클레임에서 chatgpt_account_id 추출(서명 검증 없음)."""
    parts = (id_token or "").split(".")
    if len(parts) < 2:
        return ""
    claims = _b64url_json(parts[1])
    if claims.get("chatgpt_account_id"):
        return str(claims["chatgpt_account_id"])
    auth = claims.get("https://api.openai.com/auth") or {}
    if isinstance(auth, dict) and auth.get("chatgpt_account_id"):
        return str(auth["chatgpt_account_id"])
    orgs = claims.get("organizations") or (auth.get("organizations") if isinstance(auth, dict) else None)
    if isinstance(orgs, list) and orgs and isinstance(orgs[0], dict) and orgs[0].get("id"):
        return str(orgs[0]["id"])
    return ""


def _account_email(id_token: str) -> str:
    parts = (id_token or "").split(".")
    if len(parts) < 2:
        return ""
    return str(_b64url_json(parts[1]).get("email") or "")


# ── 저장/로드 ──────────────────────────────────────────────────────────────
def load_auth() -> dict:
    try:
        return json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_auth(data: dict) -> None:
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def logout() -> None:
    AUTH_PATH.unlink(missing_ok=True)


def is_logged_in() -> bool:
    d = load_auth()
    return bool(d.get("access") and d.get("refresh"))


def status() -> dict:
    """UI 표시용: {logged_in, email, account_id, expires_at(초)}."""
    d = load_auth()
    return {
        "logged_in": bool(d.get("access")),
        "email": d.get("email", ""),
        "account_id": d.get("accountId", ""),
        "expires_at": (d.get("expires", 0) or 0) / 1000.0,
    }


def _store_token_response(tok: dict, *, prev: Optional[dict] = None) -> dict:
    """토큰 응답 → auth.json 스키마로 저장."""
    prev = prev or {}
    id_token = tok.get("id_token") or prev.get("id_token", "")
    account_id = _account_id_from_id_token(id_token) or prev.get("accountId", "")
    data = {
        "type": "oauth",
        "access": tok.get("access_token") or prev.get("access", ""),
        "refresh": tok.get("refresh_token") or prev.get("refresh", ""),
        "id_token": id_token,
        "accountId": account_id,
        "email": _account_email(id_token) or prev.get("email", ""),
        "expires": int((time.time() + int(tok.get("expires_in", 3600))) * 1000),
    }
    save_auth(data)
    return data


# ── 콜백 서버 ──────────────────────────────────────────────────────────────
class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/auth/callback"):
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = (qs.get("code") or [""])[0]        # type: ignore[attr-defined]
        self.server.auth_state = (qs.get("state") or [""])[0]      # type: ignore[attr-defined]
        self.server.done = True                                    # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body style='font-family:sans-serif;text-align:center;margin-top:80px'>"
            "<h2>ChatGPT 로그인 완료</h2><p>이 창을 닫고 앱으로 돌아가세요.</p>"
            "</body></html>".encode("utf-8")
        )

    def log_message(self, *args):  # 콘솔 로그 억제
        return


def _serve_until_callback(port: int, timeout: float) -> Optional[HTTPServer]:
    try:
        httpd = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    except OSError:
        return None
    httpd.auth_code = ""      # type: ignore[attr-defined]
    httpd.auth_state = ""     # type: ignore[attr-defined]
    httpd.done = False        # type: ignore[attr-defined]
    httpd.timeout = 1.0
    return httpd


# ── 공개 API ───────────────────────────────────────────────────────────────
def login(*, timeout: float = 300.0) -> Tuple[bool, str]:
    """브라우저 PKCE 로그인(콜백 수신까지 블로킹). (성공여부, 메시지)."""
    httpd = None
    port = None
    for p in CALLBACK_PORTS:
        httpd = _serve_until_callback(p, timeout)
        if httpd is not None:
            port = p
            break
    if httpd is None:
        return False, f"콜백 포트({CALLBACK_PORTS})를 열 수 없습니다. 다른 프로세스가 사용 중인지 확인하세요."

    redirect_uri = f"http://localhost:{port}/auth/callback"
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "instructional-design-agent",
        "state": state,
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    try:
        webbrowser.open(auth_url)
    except Exception:  # noqa: BLE001
        pass
    print(f"[oauth] 브라우저에서 로그인하세요: {auth_url}", flush=True)

    deadline = time.time() + timeout
    while not getattr(httpd, "done", False) and time.time() < deadline:
        httpd.handle_request()
    code = getattr(httpd, "auth_code", "")
    got_state = getattr(httpd, "auth_state", "")
    try:
        httpd.server_close()
    except Exception:  # noqa: BLE001
        pass

    if not code:
        return False, "로그인 시간이 초과되었거나 취소되었습니다."
    if got_state and got_state != state:
        return False, "상태값(state) 불일치 — 보안상 중단했습니다. 다시 시도하세요."

    try:
        r = _requests().post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        }, timeout=30)
        if r.status_code != 200:
            return False, f"토큰 교환 실패(HTTP {r.status_code}): {r.text[:200]}"
        data = _store_token_response(r.json())
    except Exception as e:  # noqa: BLE001
        return False, f"토큰 교환 오류: {type(e).__name__}: {e}"

    who = data.get("email") or data.get("accountId") or "계정"
    return True, f"로그인 완료 · {who}"


def refresh() -> bool:
    """refresh_token 으로 access_token 갱신. 성공 시 True."""
    d = load_auth()
    rt = d.get("refresh")
    if not rt:
        return False
    try:
        r = _requests().post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": CLIENT_ID,
            "scope": SCOPE,
        }, timeout=30)
        if r.status_code != 200:
            print(f"[oauth] 토큰 갱신 실패 HTTP {r.status_code}: {r.text[:160]}", flush=True)
            return False
        _store_token_response(r.json(), prev=d)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[oauth] 토큰 갱신 오류: {e}", flush=True)
        return False


def get_access(*, allow_refresh: bool = True) -> Optional[Tuple[str, str]]:
    """유효한 (access_token, account_id) 반환. 만료 임박 시 선제 갱신. 미로그인 시 None."""
    d = load_auth()
    if not d.get("access"):
        return None
    if allow_refresh and time.time() * 1000 > (d.get("expires", 0) - _REFRESH_MARGIN_S * 1000):
        if refresh():
            d = load_auth()
    return d.get("access", ""), d.get("accountId", "")
