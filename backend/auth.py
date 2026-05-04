import hashlib
import uuid
from typing import Optional
from backend.storage import (
    create_user, get_user_by_username, get_user_by_email,
    create_token, delete_token, get_user_by_token,
)


def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = uuid.uuid4().hex[:16]
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def register_user(username: str, email: str, password: str, display_name: str = "") -> dict:
    if not username or not email or not password:
        return {"error": "All fields are required"}
    if len(password) < 4:
        return {"error": "Password must be at least 4 characters"}
    if get_user_by_username(username):
        return {"error": "Username already taken"}
    if get_user_by_email(email):
        return {"error": "Email already registered"}

    hashed, salt = hash_password(password)
    user_id = uuid.uuid4().hex[:8]
    user = create_user(user_id, username, email, hashed, salt, display_name or username)
    token = create_token(user_id)
    return {"user": user, "token": token}


def login_user(identifier: str, password: str) -> dict:
    user = get_user_by_username(identifier) or get_user_by_email(identifier)
    if not user:
        return {"error": "User not found"}
    hashed, _ = hash_password(password, user["password_salt"])
    if hashed != user["password_hash"]:
        return {"error": "Invalid password"}
    token = create_token(user["id"])
    return {"user": user, "token": token}


def verify_token(token: str) -> Optional[dict]:
    return get_user_by_token(token)


def logout_user(token: str):
    delete_token(token)
