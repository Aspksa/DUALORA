"""Pure layout planning for mouse crossing between two extended desktops."""

def arrange_side_by_side(displays, side):
    if side not in ("left", "right"):
        raise ValueError("Side must be left or right")
    if len(displays) != 2:
        raise ValueError("Exactly two active desktop displays required")
    if len({d["device"] for d in displays}) != 2:
        raise ValueError("Duplicate display device")
    # The primary Windows desktop generally contains (0,0).
    primary = next((d for d in displays if d["x"] <= 0 < d["x"] + d["width"]
                    and d["y"] <= 0 < d["y"] + d["height"]), displays[0])
    secondary = next(d for d in displays if d["device"] != primary["device"])
    if min(primary["width"], primary["height"], secondary["width"], secondary["height"]) <= 0:
        raise ValueError("Invalid monitor dimensions")
    x = primary["x"] + primary["width"] if side == "right" else primary["x"] - secondary["width"]
    # Align top edges so the pointer can cross across the whole shorter screen edge.
    return [{"device": d["device"], "x": d["x"] if d["device"] == primary["device"] else x,
             "y": d["y"] if d["device"] == primary["device"] else primary["y"],
             "width": d["width"], "height": d["height"]} for d in displays]
