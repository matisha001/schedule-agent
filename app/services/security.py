"""密码哈希工具：PBKDF2-HMAC-SHA256，格式 pbkdf2_sha256$iter$salt_hex$hash_hex。

不引入第三方密码库（bcrypt/passlib 在 Python 3.14 兼容性差），
用标准库 hashlib + secrets 实现，安全性满足常规业务登录场景。
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000  # OWASP 2023 对 PBKDF2-HMAC-SHA256 的建议迭代数


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hex = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (ValueError, TypeError):
        return False
