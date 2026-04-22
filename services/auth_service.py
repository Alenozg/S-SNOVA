"""
Kimlik doğrulama servisi.
Admin: ozalentrade@gmail.com / 989898
Diğer kullanıcılar kayıt olabilir.
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional

from database.db_manager import fetch_one, execute


def _hash_password(password: str) -> str:
    salt = "sisnova_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def seed_admin() -> None:
    """Admin yoksa oluştur."""
    existing = fetch_one("SELECT id FROM users WHERE email=?", ("ozalentrade@gmail.com",))
    if not existing:
        execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (?,?,?,?)",
            ("ozalentrade@gmail.com", _hash_password("989898"), "Admin", "admin"),
        )


def login(email: str, password: str) -> Optional[dict]:
    """Başarılıysa user dict döner, yoksa None."""
    user = fetch_one(
        "SELECT * FROM users WHERE email=? AND is_active=1",
        (email.strip().lower(),),
    )
    if not user:
        return None
    if user["password_hash"] != _hash_password(password):
        return None
    execute(
        "UPDATE users SET last_login=? WHERE id=?",
        (datetime.now().isoformat(), user["id"]),
    )
    return user


def register(email: str, password: str, full_name: str) -> tuple[bool, str]:
    """Yeni kullanıcı kaydı. (success, mesaj)"""
    email = email.strip().lower()
    if not email or not password or not full_name:
        return False, "Tüm alanlar zorunludur."
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalıdır."
    existing = fetch_one("SELECT id FROM users WHERE email=?", (email,))
    if existing:
        return False, "Bu e-posta zaten kayıtlı."
    execute(
        "INSERT INTO users (email, password_hash, full_name, role) VALUES (?,?,?,?)",
        (email, _hash_password(password), full_name.strip(), "user"),
    )
    return True, "Kayıt başarılı."


def list_users() -> list[dict]:
    from database.db_manager import fetch_all
    return fetch_all("SELECT id,email,full_name,role,is_active,created_at,last_login FROM users ORDER BY created_at")


def set_active(user_id: int, active: bool) -> None:
    execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))


def change_password(user_id: int, new_password: str) -> None:
    execute("UPDATE users SET password_hash=? WHERE id=?",
            (_hash_password(new_password), user_id))
