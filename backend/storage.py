import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "data.json")
_lock = threading.Lock()
MAX_STORES = 10


def _read() -> Dict[str, Any]:
    with _lock:
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"users": {}, "tokens": {}, "stores": {}, "ratings": [], "community_recipes": {}}


def _write(data: Dict[str, Any]) -> None:
    with _lock:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── User CRUD ─────────────────────────────────────────────────
def create_user(user_id, username, email, password_hash, password_salt, display_name):
    data = _read()
    user = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "password_salt": password_salt,
        "display_name": display_name,
        "bio": "",
        "avatar_base64": "",
        "created_at": _now(),
    }
    data["users"][user_id] = user
    _write(data)
    return _safe_user(user)


def get_user(user_id: str) -> Optional[dict]:
    data = _read()
    return data["users"].get(user_id)


def get_user_by_username(username: str) -> Optional[dict]:
    data = _read()
    for u in data["users"].values():
        if u["username"].lower() == username.lower():
            return u
    return None


def get_user_by_email(email: str) -> Optional[dict]:
    data = _read()
    for u in data["users"].values():
        if u["email"].lower() == email.lower():
            return u
    return None


def update_user(user_id: str, updates: dict) -> Optional[dict]:
    data = _read()
    if user_id not in data["users"]:
        return None
    allowed = {"display_name", "bio", "avatar_base64"}
    for k, v in updates.items():
        if k in allowed:
            data["users"][user_id][k] = v
    _write(data)
    return _safe_user(data["users"][user_id])


def _safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k not in ("password_hash", "password_salt")}


# ── Token CRUD ────────────────────────────────────────────────
def create_token(user_id: str) -> str:
    data = _read()
    # Remove old tokens for this user
    old = [t for t, uid in data["tokens"].items() if uid == user_id]
    for t in old:
        del data["tokens"][t]
    token = uuid.uuid4().hex
    data["tokens"][token] = user_id
    _write(data)
    return token


def get_user_by_token(token: str) -> Optional[dict]:
    data = _read()
    user_id = data["tokens"].get(token)
    if not user_id:
        return None
    user = data["users"].get(user_id)
    if not user:
        return None
    return _safe_user(user)


def delete_token(token: str):
    data = _read()
    data["tokens"].pop(token, None)
    _write(data)


# ── Store CRUD ────────────────────────────────────────────────
def create_store(user_id: str, name: str, groceries: dict, family: list) -> dict:
    data = _read()
    user_stores = [s for s in data["stores"].values() if s["user_id"] == user_id]
    if len(user_stores) >= MAX_STORES:
        return {"error": f"Maximum of {MAX_STORES} kitchens reached. Please delete one first."}

    store_id = uuid.uuid4().hex[:8]
    store = {
        "id": store_id,
        "user_id": user_id,
        "name": name or "My Kitchen",
        "groceries": groceries,
        "family": family,
        "target_days": None,
        "daily_consumption": {},
        "estimated_days": 0,
        "meal_plan": [],
        "current_recipe": None,
        "current_step": 0,
        "recipe_steps": [],
        "is_cooking_complete": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["stores"][store_id] = store
    _write(data)
    return store


def get_store(store_id: str) -> Optional[dict]:
    data = _read()
    return data["stores"].get(store_id)


def get_user_stores(user_id: str) -> List[dict]:
    data = _read()
    stores = [s for s in data["stores"].values() if s["user_id"] == user_id]
    stores.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return stores


def update_store(store_id: str, updates: dict) -> Optional[dict]:
    data = _read()
    if store_id not in data["stores"]:
        return None
    data["stores"][store_id].update(updates)
    data["stores"][store_id]["updated_at"] = _now()
    _write(data)
    return data["stores"][store_id]


def delete_store(store_id: str) -> bool:
    data = _read()
    if store_id in data["stores"]:
        del data["stores"][store_id]
        _write(data)
        return True
    return False


def get_user_store_count(user_id: str) -> int:
    data = _read()
    return sum(1 for s in data["stores"].values() if s["user_id"] == user_id)


# ── Ratings CRUD ──────────────────────────────────────────────
def add_rating(user_id, store_id, meal_name, stars, comment):
    data = _read()
    rating = {
        "user_id": user_id,
        "store_id": store_id,
        "meal_name": meal_name,
        "stars": stars,
        "comment": comment,
        "created_at": _now(),
    }
    data["ratings"].append(rating)
    key = meal_name.lower().strip()
    if key not in data["community_recipes"]:
        data["community_recipes"][key] = {"total_stars": 0, "count": 0, "comments": []}
    data["community_recipes"][key]["total_stars"] += stars
    data["community_recipes"][key]["count"] += 1
    data["community_recipes"][key]["comments"].append({"stars": stars, "comment": comment})
    _write(data)
    return rating


def get_ratings(limit=50):
    data = _read()
    return list(reversed(data["ratings"][-limit:]))


def get_community_recipes():
    data = _read()
    return data.get("community_recipes", {})
