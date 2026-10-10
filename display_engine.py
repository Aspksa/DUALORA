"""Display details and named monitor position profiles for Windows."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform

PROFILE_PATH = Path.home() / "DUALORA" / "profiles.json"

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class VIEW(ctypes.Structure):
    _fields_ = [("position", POINT), ("orientation", wintypes.DWORD),
                ("fixed", wintypes.DWORD)]

class PRINTER(ctypes.Structure):
    _fields_ = [(n, wintypes.SHORT) for n in ("orientation", "paperSize", "paperLength",
                "paperWidth", "scale", "copies", "defaultSource", "printQuality")]

class UNION(ctypes.Union):
    _fields_ = [("view", VIEW), ("printer", PRINTER)]

class DEVMODE(ctypes.Structure):
    _fields_ = [("name", wintypes.WCHAR * 32), ("spec", wintypes.WORD),
        ("driver", wintypes.WORD), ("size", wintypes.WORD), ("extra", wintypes.WORD),
        ("fields", wintypes.DWORD), ("kind", UNION),
        ("color", wintypes.SHORT), ("duplex", wintypes.SHORT),
        ("yres", wintypes.SHORT), ("tt", wintypes.SHORT),
        ("collate", wintypes.SHORT), ("form", wintypes.WCHAR * 32),
        ("dpi", wintypes.WORD), ("bpp", wintypes.DWORD),
        ("width", wintypes.DWORD), ("height", wintypes.DWORD),
        ("flags", wintypes.DWORD), ("hz", wintypes.DWORD),
        ("icm", wintypes.DWORD), ("intent", wintypes.DWORD),
        ("media", wintypes.DWORD), ("dither", wintypes.DWORD),
        ("reserved1", wintypes.DWORD), ("reserved2", wintypes.DWORD),
        ("panwidth", wintypes.DWORD), ("panheight", wintypes.DWORD)]

class DEVICE(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("name", wintypes.WCHAR * 32),
        ("description", wintypes.WCHAR * 128), ("state", wintypes.DWORD),
        ("identifier", wintypes.WCHAR * 128), ("key", wintypes.WCHAR * 128)]

def enumerate_displays():
    if platform.system() != "Windows":
        raise RuntimeError("Windows required")
    api = ctypes.WinDLL("user32", use_last_error=True)
    devices = api.EnumDisplayDevicesW
    devices.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                        ctypes.POINTER(DEVICE), wintypes.DWORD]
    devices.restype = wintypes.BOOL
    modes = api.EnumDisplaySettingsW
    modes.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODE)]
    modes.restype = wintypes.BOOL
    result = []
    index = 0
    while True:
        d = DEVICE()
        d.cb = ctypes.sizeof(d)
        if not devices(None, index, ctypes.byref(d), 0):
            break
        index += 1
        if not d.state & 1:
            continue
        m = DEVMODE()
        m.size = ctypes.sizeof(m)
        if not modes(d.name, 0xffffffff, ctypes.byref(m)):
            continue
        monitor = DEVICE()
        monitor.cb = ctypes.sizeof(monitor)
        found = devices(d.name, 0, ctypes.byref(monitor), 0)
        result.append({"device": d.name, "adapter": d.description,
            "monitor": monitor.description if found else "",
            "monitor_id": monitor.identifier if found else "",
            "x": m.kind.view.position.x, "y": m.kind.view.position.y,
            "width": m.width, "height": m.height, "hz": m.hz})
    return result

def position_snapshot(devices):
    return [{"device": d["device"], "x": int(d["x"]), "y": int(d["y"]),
             "width": int(d["width"]), "height": int(d["height"])} for d in devices]

def validate(snapshot, current):
    if not isinstance(snapshot, list) or len(snapshot) != len(current) or not current:
        raise ValueError("Different number of connected screens")
    lookup = {d["device"]: d for d in current}
    if len(lookup) != len(current) or len(set(d.get("device") for d in snapshot)) != len(snapshot):
        raise ValueError("Duplicate monitor")
    for d in snapshot:
        old = lookup.get(d.get("device"))
        if old is None or (d.get("width"), d.get("height")) != (old["width"], old["height"]):
            raise ValueError("Monitor missing or resolution changed")
        for coord in ("x", "y"):
            if type(d.get(coord)) is not int or abs(d[coord]) > 100000:
                raise ValueError("Invalid screen position")

def read_profiles(path=PROFILE_PATH):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def save_profile(name, screens, path=PROFILE_PATH):
    if not name or len(name) > 60:
        raise ValueError("Profile name must be 1-60 characters")
    profiles = read_profiles(path)
    profiles[name] = position_snapshot(screens)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)

def apply_positions(snapshot):
    current = enumerate_displays()
    validate(snapshot, current)
    api = ctypes.WinDLL("user32", use_last_error=True)
    modes = api.EnumDisplaySettingsW
    modes.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODE)]
    modes.restype = wintypes.BOOL
    change = api.ChangeDisplaySettingsExW
    change.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(DEVMODE),
                       wintypes.HWND, wintypes.DWORD, wintypes.LPVOID]
    change.restype = wintypes.LONG
    staged = []
    for d in snapshot:
        mode = DEVMODE()
        mode.size = ctypes.sizeof(mode)
        if not modes(d["device"], 0xffffffff, ctypes.byref(mode)):
            raise RuntimeError("Unable to read current mode")
        mode.fields = 0x20
        mode.kind.view.position.x = d["x"]
        mode.kind.view.position.y = d["y"]
        if change(d["device"], ctypes.byref(mode), None, 0x2, None) != 0:
            raise RuntimeError("Display rejects new position")
        staged.append((d["device"], mode))
    for name, mode in staged:
        if change(name, ctypes.byref(mode), None, 0x10000000, None) != 0:
            raise RuntimeError("Failed to stage position")
    if change(None, None, None, 0, None) != 0:
        raise RuntimeError("Failed to apply positions")
