"""Safe local wallpaper selection, Windows-account display and refresh guidance."""
from pathlib import Path
import ctypes
import getpass
import platform

SUPPORTED = {".bmp", ".jpg", ".jpeg", ".png"}
FIVE_K = (5120, 2880)

def wallpaper_candidate(path):
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    if candidate.suffix.lower() not in SUPPORTED:
        raise ValueError("Choose BMP, JPG, JPEG or PNG")
    return candidate

def account_label():
    # Reuses the signed-in Windows session; never asks for or stores passwords.
    return getpass.getuser()

def apply_wallpaper(path):
    if platform.system() != "Windows":
        raise RuntimeError("Wallpaper changes are supported only on Windows")
    candidate = wallpaper_candidate(path)
    spi = ctypes.WinDLL("user32", use_last_error=True).SystemParametersInfoW
    spi.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    spi.restype = ctypes.c_int
    if not spi(0x0014, 0, str(candidate), 0x01 | 0x02):
        raise ctypes.WinError(ctypes.get_last_error())
    return str(candidate)

def refresh_explanation(hz):
    return ("Частота экрана: " + str(hz) + " Гц. Это не FPS игры: "
            "реальное количество кадров зависит от игры, GPU, CPU и настроек.")
