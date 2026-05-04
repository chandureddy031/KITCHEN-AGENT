import uvicorn
import os
import json

os.makedirs("database", exist_ok=True)
os.makedirs("frontend/templates", exist_ok=True)

db_path = os.path.join("database", "data.json")
if not os.path.exists(db_path):
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({
            "users": {},
            "tokens": {},
            "stores": {},
            "ratings": [],
            "community_recipes": {}
        }, f, indent=2)

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
