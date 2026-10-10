"""Video-mode recommendations. Maximum resolution is not necessarily native resolution."""
def recommend(modes):
    seen = {(int(m["width"]), int(m["height"]), int(m["hz"])) for m in modes if
            int(m["width"]) >= 640 and int(m["height"]) >= 480 and int(m["hz"]) >= 30}
    if not seen:
        return {}
    best_sharp = max(seen, key=lambda m: (m[0]*m[1], m[2]))
    best_smooth = max(seen, key=lambda m: (m[2], m[0]*m[1]))
    pool = [m for m in seen if m[2] >= 60] or list(seen)
    balanced = max(pool, key=lambda m: (m[0]*m[1], m[2]))
    return {key: dict(zip(("width","height","hz"), value)) for key,value in
            (("sharp",best_sharp),("smooth",best_smooth),("balanced",balanced))}
