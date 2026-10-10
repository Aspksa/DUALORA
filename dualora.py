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
from tkinter import ttk, messagebox, simpledialog
from display_engine import enumerate_displays, position_snapshot, read_profiles, save_profile, apply_positions
from datetime import datetime

APP_VERSION = "0.3.0"
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
        self.details = []
        self.identifiers = []
        self.error = None
        ttk.Button(extras, text="Сохранить профиль", command=self.save_layout).pack(side="left", padx=4)
        ttk.Button(extras, text="Применить профиль", command=self.restore_layout).pack(side="left", padx=4)
        self.diagram = tk.Canvas(host, height=140, bg="#172337", highlightthickness=0)
        self.diagram.pack(fill="x", pady=(8, 4))
        self.diagram.bind("<Configure>", lambda event: self.draw_diagram())
        tools = ttk.Frame(host)
        tools.pack(fill="x", pady=4)
        ttk.Button(tools, text="Мастер чёрного экрана", command=self.troubleshoot).pack(side="left", padx=4)
        ttk.Button(tools, text="Профиль Работа", command=lambda: self.quick_profile("Работа")).pack(side="left", padx=4)
        ttk.Button(tools, text="Профиль Игры", command=lambda: self.quick_profile("Игры")).pack(side="left", padx=4)
        self.refresh()

    def draw_diagram(self):
        if not hasattr(self, "diagram"):
            return
        canvas = self.diagram
        canvas.delete("all")
        screens = self.details
        if not screens:
            canvas.create_text(20, 65, anchor="w", fill="#e5edfa",
                               text="Нет активных видеорежимов. Нажмите «Обновить диагностику».")
            return
        min_x = min(d["x"] for d in screens)
        min_y = min(d["y"] for d in screens)
        full_w = max(d["x"] + d["width"] for d in screens) - min_x
        full_h = max(d["y"] + d["height"] for d in screens) - min_y
        scale = min((max(canvas.winfo_width(), 300) - 50) / max(full_w, 1),
                    110 / max(full_h, 1))
        for index, d in enumerate(screens, 1):
            x = 20 + (d["x"] - min_x) * scale
            y = 12 + (d["y"] - min_y) * scale
            w = d["width"] * scale
            h = d["height"] * scale
            canvas.create_rectangle(x, y, x + w, y + h, outline="#58c7ff",
                                    fill="#263e59", width=2)
            canvas.create_text(x + w / 2, y + h / 2, fill="white",
                               text=f"{index} · {d['width']}×{d['height']}")
        canvas.create_text(20, 132, anchor="w", fill="#93aac6",
                           text="Схема расположения (для изменения выберите профиль)")

    def quick_profile(self, name):
        try:
            profiles = read_profiles()
            if name in profiles:
                self.apply_named_profile(name, profiles[name])
            elif messagebox.askyesno("Новый профиль", f"Сохранить текущее расположение как «{name}»?"):
                save_profile(name, enumerate_displays())
                messagebox.showinfo("Готово", "Профиль сохранён.")
        except Exception as exc:
            messagebox.showerror("Профиль", str(exc))

    def troubleshoot(self):
        count = len(self.details)
        matches = [d for d in self.details if "AQ32H3" in
                   (d["monitor"] + d["monitor_id"]).upper()]
        if count >= 2:
            status = "Windows сообщает о нескольких активных видеорежимах."
        else:
            status = "Windows не подтверждает второй активный рабочий экран."
        model = ("AQ32H3 обнаружен в активном видеорежиме." if matches else
                 "AQ32H3 не идентифицирован по имени активного видеовыхода.")
        messagebox.showinfo("Мастер диагностики AQ32H3",
            status + "\n" + model + "\n\n"
            "1. Выберите на мониторе нужный HDMI / DP через Input / Source.\n"
            "2. Проверьте соединение кабеля с двух сторон.\n"
            "3. Выберите «Расширить экраны», затем обновите диагностику.\n"
            "4. В параметрах Windows проверьте разрешение и частоту 60 Гц (если доступна).\n\n"
            "Важно: ПО не способно измерить физический HDMI/DP-сигнал.")

    def apply_named_profile(self, name, profile):
        previous = position_snapshot(enumerate_displays())
        if not messagebox.askyesno("Подтверждение", f"Применить профиль «{name}»?"):
            return
        apply_positions(profile)
        # Tk message boxes enter a nested event loop on Windows, allowing after()
        # to enforce the timeout even without another user action.
        state = {"done": False}
        def revert():
            if not state["done"]:
                state["done"] = True
                try:
                    apply_positions(previous)
                except Exception as exc:
                    messagebox.showerror("Откат", str(exc))
        timer = self.root.after(15000, revert)
        accepted = messagebox.askyesno("Проверка расположения", "Всё видно? Сохранить новое расположение.")
        if accepted and not state["done"]:
            state["done"] = True
            self.root.after_cancel(timer)
        elif not state["done"]:
            self.root.after_cancel(timer)
            revert()
        self.refresh()

    def save_layout(self):
        if not self.details:
            messagebox.showwarning("Нет экранов", "Обновите диагностику.")
            return
        name = simpledialog.askstring("Профиль", "Название:", parent=self.root)
        if name is None:
            return
        try:
            save_profile(name, self.details)
            messagebox.showinfo("Готово", "Профиль сохранён.")
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))

    def restore_layout(self):
        try:
            profiles = read_profiles()
            if not profiles:
                messagebox.showinfo("Профили", "Пока нет сохранённых профилей.")
                return
            name = simpledialog.askstring("Профили", "Название профиля:\n" + "\n".join(profiles), parent=self.root)
            if name is None:
                return
            if name not in profiles:
                messagebox.showwarning("Профили", "Профиль не найден.")
                return
            previous = position_snapshot(enumerate_displays())
            if not messagebox.askyesno("Безопасность", "Применить профиль? Подтвердите новый вид в течение 15 секунд."):
                return
            apply_positions(profiles[name])
            state = {"finished": False}
            def revert():
                if not state["finished"]:
                    state["finished"] = True
                    try:
                        apply_positions(previous)
                    except Exception as exc:
                        messagebox.showerror("Откат не удался", str(exc))
            timer = self.root.after(15000, revert)
            ok = messagebox.askyesno("Экран", "Всё видно на обоих экранах? Сохранить расположение?")
            if ok and not state["finished"]:
                state["finished"] = True
                self.root.after_cancel(timer)
            elif not state["finished"]:
                self.root.after_cancel(timer)
                revert()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Ошибка профиля", str(exc))
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
        try:
            self.details = enumerate_displays()
        except Exception as exc:
            self.details = []
            self.error = (self.error or "") + " / details: " + str(exc)
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
        lines += ["", "ИДЕНТИФИКАЦИЯ МОНИТОРОВ / ВИДЕОРЕЖИМЫ"]
        for d in self.details:
            lines.append(f"{d['device']}: {d['monitor']} | {d['width']}x{d['height']} @ {d['hz']} Hz | ({d['x']}, {d['y']})")
            lines.append("  Device ID: " + d["monitor_id"])
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
        self.draw_diagram()

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
                   "wmi_monitors": self.identifiers, "display_modes": self.details, "error": self.error}
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
