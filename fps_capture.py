"""Read real frame-time samples from a PresentMon CSV capture.

DUALORA does not fabricate FPS. PresentMon must be recording a supported game.
"""
import csv
from pathlib import Path
import statistics

def load_presentmon(path, limit=5000):
    if not isinstance(limit,int) or limit<1 or limit>100000: raise ValueError("Invalid limit")
    p=Path(path)
    if not p.is_file(): raise FileNotFoundError(str(p))
    with p.open("r",encoding="utf-8-sig",newline="",errors="replace") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: raise ValueError("CSV has no header")
        col=next((c for c in ("MsBetweenPresents","MsBetweenDisplayChange","FrameTime")
                 if c in reader.fieldnames),None)
        if not col: raise ValueError("PresentMon CSV needs MsBetweenPresents, MsBetweenDisplayChange or FrameTime")
        data=[]
        for row in reader:
            try:
                ms=float(row[col])
                if 0.1<=ms<=10000 and ms==ms: data.append(ms)
            except (ValueError,TypeError): pass
            if len(data)>limit: data.pop(0)
    return data

def summary(samples):
    if not samples: return {"frames":0,"fps":None,"one_percent_low":None,"average_ms":None,"stutters":0}
    ordered=sorted(samples,reverse=True)
    n=max(1,len(samples)//100)
    mean_ms=statistics.mean(samples)
    # Slowest 1% of frame times, interpreted as harmonic-equivalent FPS.
    low_ms=statistics.mean(ordered[:n])
    threshold=max(50.0,2*statistics.median(samples))
    return {"frames":len(samples),"fps":round(1000/mean_ms,1),
            "one_percent_low":round(1000/low_ms,1),
            "average_ms":round(mean_ms,2),
            "stutters":sum(x>threshold for x in samples)}
