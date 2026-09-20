"""登录 token：HMAC-SHA256 签名，无状态（uid + 过期时间）。

格式：base64url(payload).base64url(signature)
payload = {"uid": int, "exp": int}
"""

import base64
import hashlib
import hmac
import json
import time

from app.conf.app_config import app_config

_SECRET = app_config.auth.token_secret.encode("utf-8")
_TTL = app_config.auth.token_ttl


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user_id: int, ttl: int | None = None) -> str:
    payload = {"uid": int(user_id), "exp": int(time.time()) + (ttl or _TTL)}
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_SECRET, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64encode(signature)}"


def verify_token(token: str) -> int | None:
    """校验 token，成功返回 uid，失败返回 None。"""
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        expected = _b64encode(
            hmac.new(_SECRET, payload_b64.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected, signature_b64):
            return None
        payload = json.loads(_b64decode(payload_b64))
        if int(payload["exp"]) < int(time.time()):
            return None
        return int(payload["uid"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
