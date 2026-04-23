"""
Kimlik doğrulama servisi.
Admin: aleyna / sisnova
Kayıt özelliği devre dışı — yalnızca admin girişi aktif.
"""
import hashlib
from datetime import datetime
from typing import Optional

from database.db_manager import fetch_one, execute


def _hash_password(password: str) -> str:
    salt = "sisnova_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def seed_admin() -> None:
    """
    Admin hesabını garantile.
    - Eski ozalentrade@gmail.com kaydı varsa güncelle.
    - Yoksa aleyna kullanıcısını oluştur.
    """
    # Eski kayıt varsa yeni bilgilere güncelle
    execute(
        """UPDATE users
           SET email=?, password_hash=?, full_name=?, role='admin', is_active=1
           WHERE email=?""",
        ("aleyna", _hash_password("sisnova"), "Aleyna", "ozalentrade@gmail.com"),
    )
    # Yukarıdaki UPDATE etkilenen satır yoksa yeni oluştur
    existing = fetch_one("SELECT id FROM users WHERE email=?", ("aleyna",))
    if not existing:
        execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (?,?,?,?)",
            ("aleyna", _hash_password("sisnova"), "Aleyna", "admin"),
        )


def login(username: str, password: str) -> Optional[dict]:
    """Başarılıysa user dict döner, yoksa None."""
    user = fetch_one(
        "SELECT * FROM users WHERE email=? AND is_active=1",
        (username.strip().lower(),),
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


def list_users() -> list[dict]:
    from database.db_manager import fetch_all
    return fetch_all(
        "SELECT id,email,full_name,role,is_active,created_at,last_login FROM users ORDER BY created_at"
    )


def set_active(user_id: int, active: bool) -> None:
    execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))


def change_password(user_id: int, new_password: str) -> None:
    execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (_hash_password(new_password), user_id),
    )
