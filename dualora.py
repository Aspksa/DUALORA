"""DUALORA — Windows multi-monitor manager (standard-library desktop app)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

APP_VERSION = "0.1.0"
REPORT_PATH = Path.home() / "DUALORA" / "diagnostics.json"


def active_displays():
    """Enumerate actual active Windows desktop display surfaces (not only EDID records)."""
    if platform.system() != "Windows":
        return []
    screens = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )
    def receive(monitor, hdc, rect, data):
        r = rect.contents
        screens.append({"index": len(screens) + 1, "left": r.left,
                        "top": r.top, "width": r.right-r.left,
                        "height": r.bottom-r.top})
        return True
    cb = callback_type(receive)
    ok = ctypes.windll.user32.EnumDisplayMonitors(None, None, cb, 0)
    if not ok:
        raise ctypes.WinError()
    return screens


def monitor_identifiers():
    """Collect WMI monitor labels separately; an EDID record isn't proof of a desktop."""
    if platform.system() != "Windows":
        return []
    script = (
        "Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID "
        "| Select-Object -Property InstanceName,Active,UserFriendlyName "
        "| ConvertTo-Json -Compress"
    )
    try:
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=12, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        raw = json.loads(p.stdout) if p.stdout.strip() else []
        return raw if isinstance(raw, list) else [raw]
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def switch_display(mode):
    if platform.system() != "Windows":
        raise RuntimeError("Only Windows is supported")
    if mode not in ("extend", "clone", "internal", "external"):
        raise ValueError("Unsupported mode")
    tool = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "DisplaySwitch.exe"
    if not tool.is_file():
        raise FileNotFoundError(str(tool))
    subprocess.Popen([str(tool), "/" + mode])


class App:
    def __init__(self, root):
        self.root = root
        root.title("DUALORA · Мониторы")
        root.geometry("760x590")
        root.minsize(640, 480)
        root.configure(bg="#101827")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#101827")
        style.configure("TLabel", foreground="#e6eef9", background="#101827", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 22), foreground="#8bd3ff")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 9))
        style.configure("TNotebook", background="#101827")
        style.configure("TNotebook.Tab", padding=(14, 9))
        host = ttk.Frame(root, padding=22)
        host.pack(fill="both", expand=True)
        ttk.Label(host, text="DUALORA", style="Header.TLabel").pack(anchor="w")
        ttk.Label(host, text="Управление экранами · Windows 10/11 · v" + APP_VERSION).pack(anchor="w", pady=(0, 14))
        self.summary = tk.StringVar(value="Ожидание диагностики...")
        ttk.Label(host, textvariable=self.summary).pack(anchor="w", pady=(0, 9))
        self.output = tk.Text(host, height=15, bg="#172337", fg="#e5edfa", insertbackground="white",
                              relief="flat", wrap="word", font=("Consolas", 10), padx=15, pady=14)
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="disabled")
        actions = ttk.Frame(host)
        actions.pack(fill="x", pady=(15, 8))
        for i, (caption, action) in enumerate([
            ("Обновить диагностику", self.refresh),
            ("Расширить экраны", lambda: self.change("extend")),
            ("Дублировать", lambda: self.change("clone")),
            ("Параметры Windows", self.settings),
        ]):
            ttk.Button(actions, text=caption, command=action).grid(row=i//2, column=i%2, sticky="ew", padx=4, pady=4)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        extras = ttk.Frame(host)
        extras.pack(fill="x")
        ttk.Button(extras, text="Сохранить отчёт", command=self.export).pack(side="left", padx=4)
        ttk.Button(extras, text="Только ноутбук", command=lambda: self.change("internal")).pack(side="left", padx=4)
        ttk.Button(extras, text="Только монитор", command=lambda: self.change("external")).pack(side="left", padx=4)
        self.displays = []
        self.identifiers = []
        self.error = None
        self.refresh()

    def write(self, message):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", message)
        self.output.configure(state="disabled")

    def refresh(self):
        self.error = None
        try:
            self.displays = active_displays()
        except Exception as exc:
            self.displays = []
            self.error = str(exc)
        self.identifiers = monitor_identifiers()
        count = len(self.displays)
        self.summary.set(f"Активных областей рабочего стола: {count}")
        lines = ["АКТИВНЫЕ ЭКРАНЫ WINDOWS", "======================="]
        if self.error:
            lines.append("Ошибка API: " + self.error)
        for d in self.displays:
            lines.append(f"Экран {d['index']}: {d['width']}×{d['height']}  X={d['left']} Y={d['top']}")
        if not self.displays:
            lines.append("Активные области не обнаружены.")
        lines += ["", f"ЗАПИСИ ПОДКЛЮЧЁННЫХ МОНИТОРОВ (WMI): {len(self.identifiers)}",
                  "Эти записи не гарантируют наличие изображения."]
        for item in self.identifiers:
            lines.append(f"• {item.get('InstanceName', 'Unknown')} · Active={item.get('Active', '?')}")
        lines += ["", "ПОДСКАЗКА"]
        if count >= 2:
            lines.append("Два экрана активны в Windows. Если один чёрный, проверьте вход HDMI/DP, кабель и частоту обновления в параметрах дисплея.")
        else:
            lines.append("Расширенный рабочий стол пока не подтверждён. Проверьте HDMI/DP, вход Source на мониторе и нажмите «Расширить экраны».")
        self.write("\n".join(lines))

    def change(self, mode):
        if not messagebox.askyesno("Изменение режима", "Windows переключит режим дисплеев. Продолжить?"):
            return
        try:
            switch_display(mode)
        except Exception as exc:
            messagebox.showerror("Не удалось переключить", str(exc))
            return
        messagebox.showinfo("Режим запрошен", "Переключение отправлено Windows. Проверьте оба экрана, затем нажмите «Обновить диагностику».")

    def settings(self):
        if platform.system() == "Windows":
            os.startfile("ms-settings:display")
        else:
            messagebox.showinfo("Windows", "Эта функция доступна только в Windows.")

    def export(self):
        payload = {"app": "DUALORA", "version": APP_VERSION, "created": datetime.now().isoformat(),
                   "platform": platform.platform(), "active_desktops": self.displays,
                   "wmi_monitors": self.identifiers, "error": self.error}
        try:
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Не удалось сохранить", str(exc))
            return
        messagebox.showinfo("Готово", f"Отчёт: {REPORT_PATH}")


if __name__ == "__main__":
    if platform.system() != "Windows":
        raise SystemExit("DUALORA needs Windows 10/11")
    app = tk.Tk()
    App(app)
    app.mainloop()
