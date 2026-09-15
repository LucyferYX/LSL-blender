"""
Find the LSL_Location_* pose file whose hand location is closest to given x, y, z coordinates.
Usage: python find_closest_location.py <x> <y> <z>
Example: python find_closest_location.py -0.044 -0.17 1.5
"""

import json
import math
import sys
from pathlib import Path

POSES_DIR = Path(__file__).parent.parent / "poses"


def find_closest(target_x: float, target_y: float, target_z: float, top_n: int = 3):
    results = []

    for path in POSES_DIR.glob("LSL_Location_*.json"):
        data = json.loads(path.read_text())
        loc = data.get("hand", {}).get("location")
        if not loc or len(loc) < 3:
            continue
        x, y, z = loc
        dist = math.sqrt((x - target_x) ** 2 + (y - target_y) ** 2 + (z - target_z) ** 2)
        results.append((dist, path.name, x, y, z))

    results.sort()
    return results[:top_n]


def main():
    if len(sys.argv) != 4:
        print("Usage: python find_closest_location.py <x> <y> <z>")
        sys.exit(1)

    try:
        tx, ty, tz = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
    except ValueError:
        print("Error: x, y, z must be numbers.")
        sys.exit(1)

    matches = find_closest(tx, ty, tz)

    if not matches:
        print("No LSL_Location_* files found or none have hand.location data.")
        sys.exit(1)

    print(f"\nTarget: ({tx}, {ty}, {tz})\n")
    print(f"{'Rank':<6} {'Distance':<12} {'File':<45} {'Hand location'}")
    print("-" * 90)
    for rank, (dist, name, x, y, z) in enumerate(matches, start=1):
        print(f"{rank:<6} {dist:<12.4f} {name:<45} ({x}, {y}, {z})")


if __name__ == "__main__":
    main()
