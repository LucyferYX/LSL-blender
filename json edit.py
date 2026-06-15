import json
from pathlib import Path

base_dir = Path(__file__).parent
json_path = base_dir / "signs.json"

# Mapping from move to duration
DURATION_BY_MOVE = {
    None: 10,
    "slide": 12,
    "checkmark": 18,
    "halfcircle": 20,
    "s_shape": 20,
}

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for components in data.values():
    move = components.get("move")

    if move in DURATION_BY_MOVE:
        components["duration"] = DURATION_BY_MOVE[move]

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
