import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRET_FILE = DATA_DIR / ".secret_key"


def get_secret() -> bytes:
    env = os.getenv("PROPERTY_OS_SECRET")
    if env:
        return env.encode("utf-8")
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        try:
            SECRET_FILE.chmod(0o600)
        except OSError:
            pass
    return SECRET_FILE.read_text(encoding="utf-8").strip().encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 390_000)
    return "pbkdf2_sha256$390000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_b64, digest_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(user_id: int, max_age: int = 60 * 60 * 24 * 7) -> str:
    expires = int(time.time()) + max_age
    payload = f"{user_id}.{expires}"
    signature = hmac.new(get_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        user_id_s, expires_s, signature = token.split(".")
        payload = f"{user_id_s}.{expires_s}"
        expected = hmac.new(get_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature) or int(expires_s) < int(time.time()):
            return None
        return int(user_id_s)
    except (ValueError, TypeError):
        return None
