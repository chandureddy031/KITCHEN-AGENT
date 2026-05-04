import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.auth import register_user, login_user, verify_token, logout_user
from backend.agent import (
    get_ingredient_meta,
    run_analysis_and_calculate,
    run_meal_suggestions,
    run_recipe_generation,
)
from backend.storage import (
    create_store, get_store, get_user_stores, update_store, delete_store,
    get_user_store_count, update_user, add_rating, get_ratings,
    get_community_recipes, MAX_STORES,
)

app = FastAPI(title="Smart Kitchen AI")
templates_dir = Path(__file__).parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# ── Auth helpers ──────────────────────────────────────────────
async def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("auth_token")
    if not token:
        return None
    return verify_token(token)


async def require_auth(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Page Routes ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def page_home(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


@app.get("/signup", response_class=HTMLResponse)
async def page_signup(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("signup.html", {"request": request, "user": None})


@app.get("/profile", response_class=HTMLResponse)
async def page_profile(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@app.get("/create", response_class=HTMLResponse)
async def page_create(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    count = get_user_store_count(user["id"])
    return templates.TemplateResponse(
        "create.html", {"request": request, "user": user, "store_count": count, "max_stores": MAX_STORES}
    )


@app.get("/edit/{store_id}", response_class=HTMLResponse)
async def page_edit(request: Request, store_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    store = get_store(store_id)
    if not store or store["user_id"] != user["id"]:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        "edit_store.html", {"request": request, "user": user, "store_id": store_id}
    )


@app.get("/dashboard/{store_id}", response_class=HTMLResponse)
async def page_dashboard(request: Request, store_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    store = get_store(store_id)
    if not store or store["user_id"] != user["id"]:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "store_id": store_id}
    )


@app.get("/cooking/{store_id}", response_class=HTMLResponse)
async def page_cooking(request: Request, store_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    store = get_store(store_id)
    if not store or store["user_id"] != user["id"]:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        "cooking.html", {"request": request, "user": user, "store_id": store_id}
    )


@app.get("/rate/{store_id}", response_class=HTMLResponse)
async def page_rate(request: Request, store_id: str):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "rate.html", {"request": request, "user": user, "store_id": store_id}
    )


# ── Auth API ──────────────────────────────────────────────────
@app.post("/api/auth/signup")
async def api_signup(request: Request):
    try:
        body = await request.json()
        result = register_user(
            body.get("username", "").strip(),
            body.get("email", "").strip(),
            body.get("password", ""),
            body.get("display_name", "").strip(),
        )
        if "error" in result:
            return JSONResponse(result, status_code=400)
        resp = JSONResponse({"success": True, "user": result["user"]})
        resp.set_cookie("auth_token", result["token"], httponly=True, max_age=86400 * 7, samesite="lax")
        return resp
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/auth/login")
async def api_login(request: Request):
    try:
        body = await request.json()
        result = login_user(body.get("username", "").strip(), body.get("password", ""))
        if "error" in result:
            return JSONResponse(result, status_code=400)
        resp = JSONResponse({"success": True, "user": result["user"]})
        resp.set_cookie("auth_token", result["token"], httponly=True, max_age=86400 * 7, samesite="lax")
        return resp
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    token = request.cookies.get("auth_token")
    if token:
        logout_user(token)
    resp = JSONResponse({"success": True})
    resp.delete_cookie("auth_token")
    return resp


# ── Profile API ───────────────────────────────────────────────
@app.get("/api/profile")
async def api_get_profile(request: Request):
    user = await require_auth(request)
    return JSONResponse({"user": user})


@app.put("/api/profile")
async def api_update_profile(request: Request):
    user = await require_auth(request)
    body = await request.json()
    updated = update_user(user["id"], body)
    return JSONResponse({"user": updated})


# ── Store API ─────────────────────────────────────────────────
@app.get("/api/stores")
async def api_list_stores(request: Request):
    user = await require_auth(request)
    stores = get_user_stores(user["id"])
    return JSONResponse({"stores": stores, "count": len(stores), "max": MAX_STORES})


@app.post("/api/stores")
async def api_create_store(request: Request):
    try:
        user = await require_auth(request)
        body = await request.json()
        groceries = body.get("groceries", {})
        family = body.get("family", [])
        name = body.get("name", "My Kitchen").strip()

        if not groceries:
            return JSONResponse({"error": "Add at least one grocery item"}, status_code=400)
        if not family:
            return JSONResponse({"error": "Add at least one family member"}, status_code=400)

        enriched = {}
        for item, info in groceries.items():
            meta = get_ingredient_meta(item)
            enriched[item] = {**info, "emoji": meta["emoji"], "img": meta["img"]}

        store = create_store(user["id"], name, enriched, family)
        if "error" in store:
            return JSONResponse(store, status_code=400)

        try:
            result = run_analysis_and_calculate(enriched, family)
            update_store(store["id"], {
                "daily_consumption": result.get("daily_consumption", {}),
                "estimated_days": result.get("estimated_days", 0),
            })
        except Exception:
            pass

        store = get_store(store["id"])
        return JSONResponse({"store": store})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/stores/{store_id}")
async def api_get_store(request: Request, store_id: str):
    user = await require_auth(request)
    store = get_store(store_id)
    if not store or store["user_id"] != user["id"]:
        return JSONResponse({"error": "Store not found"}, status_code=404)
    return JSONResponse({"store": store})


@app.put("/api/stores/{store_id}")
async def api_update_store(request: Request, store_id: str):
    try:
        user = await require_auth(request)
        store = get_store(store_id)
        if not store or store["user_id"] != user["id"]:
            return JSONResponse({"error": "Store not found"}, status_code=404)

        body = await request.json()
        updates = {}

        if "name" in body:
            updates["name"] = body["name"].strip()

        if "groceries" in body:
            enriched = {}
            for item, info in body["groceries"].items():
                meta = get_ingredient_meta(item)
                enriched[item] = {**info, "emoji": meta["emoji"], "img": meta["img"]}
            updates["groceries"] = enriched

        if "family" in body:
            updates["family"] = body["family"]

        # Reset meal plan when groceries or family change
        if "groceries" in body or "family" in body:
            updates["meal_plan"] = []
            updates["daily_consumption"] = {}
            updates["estimated_days"] = 0
            updates["target_days"] = None
            updates["recipe_steps"] = []
            updates["current_recipe"] = None
            updates["current_step"] = 0
            updates["is_cooking_complete"] = False

            # Re-analyze
            g = updates.get("groceries", store["groceries"])
            f = updates.get("family", store["family"])
            try:
                result = run_analysis_and_calculate(g, f)
                updates["daily_consumption"] = result.get("daily_consumption", {})
                updates["estimated_days"] = result.get("estimated_days", 0)
            except Exception:
                pass

        updated = update_store(store_id, updates)
        return JSONResponse({"store": updated})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/stores/{store_id}")
async def api_delete_store(request: Request, store_id: str):
    user = await require_auth(request)
    store = get_store(store_id)
    if not store or store["user_id"] != user["id"]:
        return JSONResponse({"error": "Store not found"}, status_code=404)
    delete_store(store_id)
    return JSONResponse({"success": True})


# ── Meal Plan API ─────────────────────────────────────────────
@app.post("/api/stores/{store_id}/plan")
async def api_plan_meals(request: Request, store_id: str):
    try:
        user = await require_auth(request)
        store = get_store(store_id)
        if not store or store["user_id"] != user["id"]:
            return JSONResponse({"error": "Store not found"}, status_code=404)

        body = await request.json()
        target_days = body.get("target_days", 7)
        update_store(store_id, {"target_days": target_days})

        result = run_meal_suggestions(store["groceries"], store["family"], target_days)
        meal_plan = result.get("meal_plan", [])
        update_store(store_id, {"meal_plan": meal_plan})

        return JSONResponse({"meal_plan": meal_plan, "target_days": target_days})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/stores/{store_id}/select-meal")
async def api_select_meal(request: Request, store_id: str):
    try:
        user = await require_auth(request)
        store = get_store(store_id)
        if not store or store["user_id"] != user["id"]:
            return JSONResponse({"error": "Store not found"}, status_code=404)

        body = await request.json()
        day = body.get("day", 1)
        meal_type = body.get("meal_type", "lunch")

        meal = None
        for day_plan in store.get("meal_plan", []):
            if day_plan.get("day") == day:
                meal = day_plan.get("meals", {}).get(meal_type)
                break

        if not meal:
            return JSONResponse({"error": "Meal not found"}, status_code=404)

        result = run_recipe_generation(meal)
        steps = result.get("recipe_steps", [])

        update_store(store_id, {
            "current_recipe": {**meal, "day": day, "meal_type": meal_type},
            "recipe_steps": steps,
            "current_step": 0,
            "is_cooking_complete": False,
        })

        return JSONResponse({"recipe": meal, "steps": steps})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/stores/{store_id}/complete-step")
async def api_complete_step(request: Request, store_id: str):
    try:
        user = await require_auth(request)
        store = get_store(store_id)
        if not store or store["user_id"] != user["id"]:
            return JSONResponse({"error": "Store not found"}, status_code=404)

        body = await request.json()
        step_index = body.get("step_index", 0)
        steps = store.get("recipe_steps", [])
        next_step = step_index + 1

        if next_step >= len(steps):
            update_store(store_id, {"current_step": next_step, "is_cooking_complete": True})
            return JSONResponse({"completed": True, "total_steps": len(steps)})
        else:
            update_store(store_id, {"current_step": next_step})
            return JSONResponse({
                "completed": False,
                "current_step": next_step,
                "next_step": steps[next_step],
                "total_steps": len(steps),
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Rating API ────────────────────────────────────────────────
@app.post("/api/rate")
async def api_rate(request: Request):
    try:
        user = await require_auth(request)
        body = await request.json()
        rating = add_rating(
            user["id"],
            body.get("store_id", ""),
            body.get("meal_name", "Unknown"),
            body.get("stars", 5),
            body.get("comment", ""),
        )
        return JSONResponse({"success": True, "rating": rating})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/ratings")
async def api_ratings(request: Request):
    return JSONResponse({"ratings": get_ratings()})


@app.get("/api/community")
async def api_community(request: Request):
    recipes = get_community_recipes()
    result = []
    for name, data in recipes.items():
        avg = data["total_stars"] / data["count"] if data["count"] > 0 else 0
        result.append({
            "name": name.title(),
            "avg_rating": round(avg, 1),
            "count": data["count"],
            "recent_comments": data["comments"][-3:],
        })
    result.sort(key=lambda x: x["avg_rating"], reverse=True)
    return JSONResponse({"recipes": result})
