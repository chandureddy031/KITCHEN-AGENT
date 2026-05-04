"""
LangGraph-powered kitchen AI agent using Groq LLM.
Handles inventory analysis, meal planning, recipe generation, and ratings.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, TypedDict

# ── Fix langchain verbose attribute compatibility ─────────────
# Newer langchain-core tries to read langchain.verbose which may
# not exist in certain version combos. Patch it before importing.
import langchain
if not hasattr(langchain, "verbose"):
    langchain.verbose = False

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from dotenv import load_dotenv
load_dotenv()
import os
# ── Configuration ─────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"

# ── Ingredient emoji & image mapping ──────────────────────────
INGREDIENT_META: Dict[str, Dict[str, str]] = {
    "tomato": {"emoji": "🍅", "img": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=200&h=200&fit=crop"},
    "onion": {"emoji": "🧅", "img": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=200&h=200&fit=crop"},
    "potato": {"emoji": "🥔", "img": "https://images.unsplash.com/photo-1590165482129-1b8b27698780?w=200&h=200&fit=crop"},
    "rice": {"emoji": "🍚", "img": "https://images.unsplash.com/photo-1536304993881-460e2e8e7734?w=200&h=200&fit=crop"},
    "chicken": {"emoji": "🍗", "img": "https://images.unsplash.com/photo-1604503449965-671bf55c2b21?w=200&h=200&fit=crop"},
    "egg": {"emoji": "🥚", "img": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=200&h=200&fit=crop"},
    "milk": {"emoji": "🥛", "img": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop"},
    "oil": {"emoji": "🫒", "img": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=200&h=200&fit=crop"},
    "garlic": {"emoji": "🧄", "img": "https://images.unsplash.com/photo-1615477550927-6ec8445a4b8a?w=200&h=200&fit=crop"},
    "ginger": {"emoji": "🫚", "img": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=200&h=200&fit=crop"},
    "chili": {"emoji": "🌶️", "img": "https://images.unsplash.com/photo-1583119022894-919a68a3d0e3?w=200&h=200&fit=crop"},
    "green chili": {"emoji": "🌶️", "img": "https://images.unsplash.com/photo-1583119022894-919a68a3d0e3?w=200&h=200&fit=crop"},
    "spinach": {"emoji": "🥬", "img": "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=200&h=200&fit=crop"},
    "carrot": {"emoji": "🥕", "img": "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=200&h=200&fit=crop"},
    "broccoli": {"emoji": "🥦", "img": "https://images.unsplash.com/photo-1459411552884-841db9b3cc2a?w=200&h=200&fit=crop"},
    "mushroom": {"emoji": "🍄", "img": "https://images.unsplash.com/photo-1504545102780-26774c1bb073?w=200&h=200&fit=crop"},
    "capsicum": {"emoji": "🫑", "img": "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=200&h=200&fit=crop"},
    "bell pepper": {"emoji": "🫑", "img": "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=200&h=200&fit=crop"},
    "corn": {"emoji": "🌽", "img": "https://images.unsplash.com/photo-1551779074-57c1b505ec14?w=200&h=200&fit=crop"},
    "bread": {"emoji": "🍞", "img": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&h=200&fit=crop"},
    "butter": {"emoji": "🧈", "img": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200&h=200&fit=crop"},
    "cheese": {"emoji": "🧀", "img": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop"},
    "paneer": {"emoji": "🧀", "img": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&h=200&fit=crop"},
    "flour": {"emoji": "🌾", "img": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=200&h=200&fit=crop"},
    "sugar": {"emoji": "🍬", "img": "https://images.unsplash.com/photo-1550052446-7c7e2ee30e54?w=200&h=200&fit=crop"},
    "salt": {"emoji": "🧂", "img": "https://images.unsplash.com/photo-1518110925495-5fe2c8531e87?w=200&h=200&fit=crop"},
    "fish": {"emoji": "🐟", "img": "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=200&h=200&fit=crop"},
    "shrimp": {"emoji": "🦐", "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=200&h=200&fit=crop"},
    "prawn": {"emoji": "🦐", "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=200&h=200&fit=crop"},
    "lemon": {"emoji": "🍋", "img": "https://images.unsplash.com/photo-1590502593747-42a996133562?w=200&h=200&fit=crop"},
    "banana": {"emoji": "🍌", "img": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=200&h=200&fit=crop"},
    "apple": {"emoji": "🍎", "img": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=200&h=200&fit=crop"},
    "avocado": {"emoji": "🥑", "img": "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=200&h=200&fit=crop"},
    "cucumber": {"emoji": "🥒", "img": "https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=200&h=200&fit=crop"},
    "coconut": {"emoji": "🥥", "img": "https://images.unsplash.com/photo-1526382551041-3c817fc3927c?w=200&h=200&fit=crop"},
    "meat": {"emoji": "🥩", "img": "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=200&h=200&fit=crop"},
    "beef": {"emoji": "🥩", "img": "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=200&h=200&fit=crop"},
    "mutton": {"emoji": "🐑", "img": "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=200&h=200&fit=crop"},
    "curd": {"emoji": "🥛", "img": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop"},
    "yogurt": {"emoji": "🥛", "img": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop"},
    "honey": {"emoji": "🍯", "img": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=200&h=200&fit=crop"},
    "cauliflower": {"emoji": "🥦", "img": "https://images.unsplash.com/photo-1568702846914-96b305d2a586?w=200&h=200&fit=crop"},
    "peas": {"emoji": "🟢", "img": "https://images.unsplash.com/photo-1563785824887-3a20e4319063?w=200&h=200&fit=crop"},
    "beans": {"emoji": "🫘", "img": "https://images.unsplash.com/photo-1564894809611-1742fc40ed80?w=200&h=200&fit=crop"},
    "lentils": {"emoji": "🫘", "img": "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?w=200&h=200&fit=crop"},
    "dal": {"emoji": "🫘", "img": "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?w=200&h=200&fit=crop"},
    "tea": {"emoji": "🍵", "img": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=200&h=200&fit=crop"},
    "coffee": {"emoji": "☕", "img": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=200&h=200&fit=crop"},
    "water": {"emoji": "💧", "img": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=200&h=200&fit=crop"},
    "pasta": {"emoji": "🍝", "img": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=200&h=200&fit=crop"},
    "noodle": {"emoji": "🍜", "img": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=200&h=200&fit=crop"},
    "noodles": {"emoji": "🍜", "img": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=200&h=200&fit=crop"},
}

DEFAULT_META = {"emoji": "🥘", "img": ""}


def get_ingredient_meta(name: str) -> Dict[str, str]:
    key = name.lower().strip()
    if key in INGREDIENT_META:
        return INGREDIENT_META[key]
    for k, v in INGREDIENT_META.items():
        if k in key or key in k:
            return v
    return DEFAULT_META


# ── State Definition ──────────────────────────────────────────
class KitchenState(TypedDict, total=False):
    groceries: Dict[str, Dict[str, Any]]
    family: List[Dict[str, Any]]
    target_days: int
    daily_consumption: Dict[str, float]
    estimated_days: int
    meal_plan: List[Dict[str, Any]]
    selected_meal_index: int
    current_recipe: Dict[str, Any]
    recipe_steps: List[Dict[str, Any]]
    current_step: int
    is_complete: bool
    error: str


# ── LLM Helper ────────────────────────────────────────────────
def get_llm(temperature: float = 0.7):
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=MODEL_NAME,
        temperature=temperature,
        max_tokens=4096,
    )


def parse_json_from_text(text: str) -> Optional[dict]:
    """Robustly extract JSON from LLM output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


# ── Node: Analyze Inventory ───────────────────────────────────
def analyze_inventory(state: KitchenState) -> KitchenState:
    llm = get_llm(temperature=0.3)

    groceries_str = "\n".join(
        [f"- {item}: {info['qty']} {info['unit']}" for item, info in state["groceries"].items()]
    )
    family_str = "\n".join(
        [
            f"- {m.get('name', 'Member')}, Age: {m.get('age', 'N/A')}, Appetite: {m.get('appetite', 'medium')}"
            for m in state["family"]
        ]
    )

    prompt = f"""You are an expert kitchen management AI. Analyze this grocery inventory and family data.

GROCERIES AVAILABLE:
{groceries_str}

FAMILY MEMBERS ({len(state['family'])} people):
{family_str}

Estimate the DAILY consumption for each grocery item based on the family size and appetite levels.
- Light appetite: ~0.7x normal
- Medium appetite: ~1.0x normal
- Heavy appetite: ~1.4x normal

Respond with ONLY valid JSON, no markdown:
{{
    "daily_consumption": {{
        "item_name": number (daily amount in same unit as input)
    }},
    "analysis_notes": "brief helpful note about the inventory balance"
}}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = parse_json_from_text(response.content)
        if result and "daily_consumption" in result:
            return {**state, "daily_consumption": result["daily_consumption"]}
    except Exception as e:
        pass

    # Fallback: simple heuristic
    family_factor = sum(
        {"light": 0.7, "medium": 1.0, "heavy": 1.4}.get(m.get("appetite", "medium"), 1.0)
        for m in state["family"]
    ) / max(len(state["family"]), 1)
    daily = {}
    for item, info in state["groceries"].items():
        daily[item] = round(info["qty"] * family_factor * 0.15, 2)
    return {**state, "daily_consumption": daily}


# ── Node: Calculate Duration ──────────────────────────────────
def calculate_duration(state: KitchenState) -> KitchenState:
    min_days = float("inf")
    for item, info in state["groceries"].items():
        daily = state.get("daily_consumption", {}).get(item, 0)
        if daily > 0:
            days_for_item = info["qty"] / daily
            min_days = min(min_days, days_for_item)

    estimated = max(int(min_days), 0) if min_days != float("inf") else 0
    return {**state, "estimated_days": estimated}


# ── Node: Suggest Meals ──────────────────────────────────────
def suggest_meals(state: KitchenState) -> KitchenState:
    llm = get_llm(temperature=0.8)

    groceries_str = "\n".join(
        [f"- {item}: {info['qty']} {info['unit']}" for item, info in state["groceries"].items()]
    )
    family_size = len(state["family"])
    target = state.get("target_days", state.get("estimated_days", 7))

    prompt = f"""You are a creative chef AI. Plan meals for {target} days.

AVAILABLE INGREDIENTS:
{groceries_str}

FAMILY SIZE: {family_size} people
TARGET: {target} days

Create a meal plan with breakfast, lunch, and dinner for each day.
Each meal should use available ingredients efficiently.
Include variety — don't repeat the same meal too often.

Respond with ONLY valid JSON:
{{
    "meal_plan": [
        {{
            "day": 1,
            "meals": {{
                "breakfast": {{
                    "name": "Meal Name",
                    "ingredients": ["item1 (qty)", "item2 (qty)"],
                    "cook_time": "15 min",
                    "difficulty": "Easy"
                }},
                "lunch": {{
                    "name": "Meal Name",
                    "ingredients": ["item1 (qty)", "item2 (qty)"],
                    "cook_time": "30 min",
                    "difficulty": "Medium"
                }},
                "dinner": {{
                    "name": "Meal Name",
                    "ingredients": ["item1 (qty)", "item2 (qty)"],
                    "cook_time": "45 min",
                    "difficulty": "Medium"
                }}
            }}
        }}
    ]
}}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = parse_json_from_text(response.content)
        if result and "meal_plan" in result:
            return {**state, "meal_plan": result["meal_plan"]}
    except Exception:
        pass

    # Fallback simple plan
    plan = []
    for day in range(1, target + 1):
        items = list(state["groceries"].keys())
        plan.append(
            {
                "day": day,
                "meals": {
                    "breakfast": {
                        "name": f"Simple {items[0] if items else 'Rice'} Bowl",
                        "ingredients": [f"{items[0]} (100g)" if items else "Rice (1 cup)"],
                        "cook_time": "15 min",
                        "difficulty": "Easy",
                    },
                    "lunch": {
                        "name": f"Mixed {' & '.join(items[:2]) if len(items) >= 2 else items[0] if items else 'Rice'} Curry",
                        "ingredients": [f"{it} (150g)" for it in items[:3]] or ["Rice (1 cup)"],
                        "cook_time": "30 min",
                        "difficulty": "Medium",
                    },
                    "dinner": {
                        "name": f"Light {' & '.join(items[:2]) if len(items) >= 2 else items[0] if items else 'Soup'} Soup",
                        "ingredients": [f"{it} (100g)" for it in items[:2]] or ["Water"],
                        "cook_time": "25 min",
                        "difficulty": "Easy",
                    },
                },
            }
        )
    return {**state, "meal_plan": plan}


# ── Standalone: Generate Recipe Steps (not part of main graph) ──
def generate_recipe_steps(state: KitchenState) -> KitchenState:
    llm = get_llm(temperature=0.6)
    recipe = state.get("current_recipe", {})
    recipe_name = recipe.get("name", "Unknown Recipe")
    ingredients = recipe.get("ingredients", [])

    prompt = f"""You are a professional chef. Create detailed step-by-step cooking instructions.

RECIPE: {recipe_name}
INGREDIENTS: {', '.join(ingredients) if isinstance(ingredients, list) else str(ingredients)}

Generate clear, numbered steps. Each step should be actionable with timing.

Respond with ONLY valid JSON:
{{
    "recipe_title": "{recipe_name}",
    "total_time": "estimated total time",
    "servings": "number of servings",
    "steps": [
        {{
            "step_number": 1,
            "title": "Step title",
            "description": "Detailed description of what to do",
            "duration": "5 min",
            "tips": "Helpful tip for this step",
            "ingredients_used": ["item1", "item2"]
        }}
    ]
}}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        result = parse_json_from_text(response.content)
        if result and "steps" in result:
            return {
                **state,
                "recipe_steps": result["steps"],
                "current_step": 0,
                "is_complete": False,
            }
    except Exception:
        pass

    # Fallback steps
    return {
        **state,
        "recipe_steps": [
            {
                "step_number": 1,
                "title": "Prepare Ingredients",
                "description": "Wash and chop all vegetables. Measure out spices and other ingredients.",
                "duration": "10 min",
                "tips": "Prep everything before you start cooking.",
                "ingredients_used": [str(i) for i in ingredients[:3]],
            },
            {
                "step_number": 2,
                "title": "Heat Oil & Add Spices",
                "description": "Heat oil in a pan. Add cumin seeds, let them splutter. Add onions and sauté until golden.",
                "duration": "8 min",
                "tips": "Don't burn the spices. Keep the heat medium.",
                "ingredients_used": ["oil", "onion"],
            },
            {
                "step_number": 3,
                "title": "Cook Main Ingredients",
                "description": "Add the main vegetables/protein. Cook until tender, stirring occasionally.",
                "duration": "15 min",
                "tips": "Cover with a lid to speed up cooking.",
                "ingredients_used": [str(i) for i in ingredients[2:5]],
            },
            {
                "step_number": 4,
                "title": "Season & Simmer",
                "description": "Add salt, turmeric, and other spices. Add water if needed. Simmer for 10 minutes.",
                "duration": "10 min",
                "tips": "Taste and adjust seasoning as needed.",
                "ingredients_used": ["salt", "turmeric"],
            },
            {
                "step_number": 5,
                "title": "Garnish & Serve",
                "description": "Garnish with fresh coriander. Serve hot with rice or bread.",
                "duration": "2 min",
                "tips": "A squeeze of lemon adds great flavor!",
                "ingredients_used": ["coriander"],
            },
        ],
        "current_step": 0,
        "is_complete": False,
    }


# ── Build LangGraph ──────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(KitchenState)

    # Only add nodes that are part of the main analysis pipeline.
    # generate_recipe_steps is called independently via run_recipe_generation().
    graph.add_node("analyze_inventory", analyze_inventory)
    graph.add_node("calculate_duration", calculate_duration)
    graph.add_node("suggest_meals", suggest_meals)

    graph.set_entry_point("analyze_inventory")
    graph.add_edge("analyze_inventory", "calculate_duration")
    graph.add_edge("calculate_duration", "suggest_meals")
    graph.add_edge("suggest_meals", END)

    return graph


# Compiled graph for full pipeline
_kitchen_graph = build_graph().compile()


def run_full_analysis(groceries: dict, family: list) -> dict:
    """Run the full analysis pipeline: analyze + calculate + suggest."""
    state: KitchenState = {
        "groceries": groceries,
        "family": family,
        "daily_consumption": {},
        "estimated_days": 0,
        "meal_plan": [],
        "recipe_steps": [],
        "current_step": 0,
        "is_complete": False,
    }
    result = _kitchen_graph.invoke(state)
    return result


def run_analysis_and_calculate(groceries: dict, family: list) -> dict:
    """Run just analyze + calculate (no meal suggestions yet)."""
    state: KitchenState = {
        "groceries": groceries,
        "family": family,
        "daily_consumption": {},
        "estimated_days": 0,
        "meal_plan": [],
        "recipe_steps": [],
        "current_step": 0,
        "is_complete": False,
    }
    state = analyze_inventory(state)
    state = calculate_duration(state)
    return state


def run_meal_suggestions(groceries: dict, family: list, target_days: int) -> dict:
    """Generate meal suggestions for a specific number of days."""
    state: KitchenState = {
        "groceries": groceries,
        "family": family,
        "target_days": target_days,
        "daily_consumption": {},
        "estimated_days": 0,
        "meal_plan": [],
        "recipe_steps": [],
        "current_step": 0,
        "is_complete": False,
    }
    state = suggest_meals(state)
    return state


def run_recipe_generation(recipe: dict) -> dict:
    """Generate step-by-step recipe instructions (standalone, not via graph)."""
    state: KitchenState = {
        "current_recipe": recipe,
        "groceries": {},
        "family": [],
        "daily_consumption": {},
        "estimated_days": 0,
        "meal_plan": [],
        "recipe_steps": [],
        "current_step": 0,
        "is_complete": False,
    }
    state = generate_recipe_steps(state)
    return state
