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
from display_engine import enumerate_displays, position_snapshot, read_profiles, save_profile, apply_positions, available_modes, apply_video_mode
from datetime import datetime
from history import add_event, read_history
from cursor_layout import arrange_side_by_side

APP_VERSION = "0.5.1"
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
        self.diagram.bind("<ButtonPress-1>", self.drag_start)
        self.diagram.bind("<B1-Motion>", self.drag_motion)
        self.diagram.bind("<ButtonRelease-1>", self.drag_end)
        self.drag_index = None
        self.drag_origin = None
        self.drag_preview = None
        self.diagram_regions = []
        self.auto_profile = tk.BooleanVar(value=False)
        self.known_devices = ()
        tools = ttk.Frame(host)
        tools.pack(fill="x", pady=4)
        ttk.Button(tools, text="Мастер чёрного экрана", command=self.troubleshoot).pack(side="left", padx=4)
        ttk.Button(tools, text="Профиль Работа", command=lambda: self.quick_profile("Работа")).pack(side="left", padx=4)
        ttk.Button(tools, text="Профиль Игры", command=lambda: self.quick_profile("Игры")).pack(side="left", padx=4)
        ttk.Button(tools, text="Видеорежим", command=self.choose_video_mode).pack(side="left", padx=4)
        ttk.Button(tools, text="Журнал", command=self.show_history).pack(side="left", padx=4)
        cursor_controls = ttk.Frame(host)
        cursor_controls.pack(fill="x", pady=(2, 5))
        ttk.Label(cursor_controls, text="Переход мыши: внешний экран").pack(side="left", padx=4)
        ttk.Button(cursor_controls, text="СЛЕВА", command=lambda: self.fix_cursor("left")).pack(side="left", padx=4)
        ttk.Button(cursor_controls, text="СПРАВА", command=lambda: self.fix_cursor("right")).pack(side="left", padx=4)
        ttk.Checkbutton(host, text="Предлагать профиль при подключении экрана",
                        variable=self.auto_profile).pack(anchor="w")
        self.refresh()
        self.known_devices = tuple(sorted(d["device"] for d in self.details))
        self.root.after(5000, self.watch_monitors)

    def draw_diagram(self):
        if not hasattr(self, "diagram"):
            return
        canvas = self.diagram
        canvas.delete("all")
        screens = self.drag_preview if self.drag_preview is not None else self.details
        self.diagram_regions = []
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
        self.diagram_scale = scale
        for index, d in enumerate(screens, 1):
            x = 20 + (d["x"] - min_x) * scale
            y = 12 + (d["y"] - min_y) * scale
            w = d["width"] * scale
            h = d["height"] * scale
            self.diagram_regions.append((x, y, x + w, y + h, index - 1))
            canvas.create_rectangle(x, y, x + w, y + h, outline="#58c7ff",
                                    fill="#263e59", width=2)
            canvas.create_text(x + w / 2, y + h / 2, fill="white",
                               text=f"{index} · {d['width']}×{d['height']}")
        canvas.create_text(20, 132, anchor="w", fill="#93aac6",
                           text="Перетащите экран мышью; для применения подтвердите изменение")


    def show_history(self):
        popup = tk.Toplevel(self.root)
        popup.title("DUALORA · Журнал событий")
        popup.geometry("760x420")
        view = tk.Text(popup, bg="#172337", fg="#e6eef9", wrap="word",
                       padx=16, pady=14, font=("Consolas", 10))
        view.pack(fill="both", expand=True)
        for entry in reversed(read_history()[-100:]):
            view.insert("end", entry["timestamp"] + "  [" + entry["type"] + "] " +
                        entry["detail"] + "\\n")
        view.configure(state="disabled")

    def audit(self, kind, detail):
        try:
            add_event(kind, detail)
        except OSError:
            pass

    def drag_start(self, event):
        for x1, y1, x2, y2, index in reversed(self.diagram_regions):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.drag_index = index
                self.drag_origin = (event.x, event.y)
                self.drag_preview = [dict(d) for d in self.details]
                break

    def drag_motion(self, event):
        if self.drag_index is None:
            return
        dx = round((event.x - self.drag_origin[0]) / max(self.diagram_scale, 0.0001))
        dy = round((event.y - self.drag_origin[1]) / max(self.diagram_scale, 0.0001))
        d = self.drag_preview[self.drag_index]
        original = self.details[self.drag_index]
        d["x"], d["y"] = original["x"] + dx, original["y"] + dy
        self.draw_diagram()

    def drag_end(self, event):
        if self.drag_index is None:
            return
        new_positions = position_snapshot(self.drag_preview)
        self.drag_index = None
        self.drag_preview = None
        self.draw_diagram()
        if new_positions != position_snapshot(self.details):
            self.apply_named_profile("Перетаскивание", new_positions)

    def choose_video_mode(self):
        if not self.details:
            messagebox.showwarning("Видео", "Нет доступных экранов")
            return
        choice = simpledialog.askinteger("Монитор", "Номер монитора от 1 до " + str(len(self.details)),
                                         minvalue=1, maxvalue=len(self.details), parent=self.root)
        if choice is None:
            return
        display = self.details[choice - 1]
        try:
            options = available_modes(display["device"])
            shown = options[:35]
            labels = [str(i) + ": " + str(m["width"]) + "x" + str(m["height"]) +
                      " @ " + str(m["hz"]) + "Hz" for i, m in enumerate(shown, 1)]
            if not shown:
                messagebox.showwarning("Видеорежим", "Режимы не обнаружены")
                return
            selected = simpledialog.askinteger("Доступные режимы", "\n".join(labels),
                                                minvalue=1, maxvalue=len(shown), parent=self.root)
            if selected is None:
                return
            if not messagebox.askyesno("Безопасность", "Временно применить режим с возможностью отката?"):
                return
            before = {key: int(display[key]) for key in ("width", "height", "hz")}
            apply_video_mode(display["device"], shown[selected-1])
            self.audit("mode", display["device"] + " -> " + str(shown[selected-1]))
            self.confirm_change(lambda: apply_video_mode(display["device"], before))
        except Exception as exc:
            messagebox.showerror("Видеорежим", str(exc))
        self.refresh()

    def confirm_change(self, rollback):
        state = {"finished": False}
        def restore():
            if state["finished"]:
                return
            state["finished"] = True
            try:
                rollback()
            except Exception as exc:
                messagebox.showerror("Ошибка отката", str(exc))
        # Dialog has a nested Tk event loop: 15-second callback can run.
        timer = self.root.after(15000, restore)
        confirmed = messagebox.askyesno("Подтверждение", "Всё видно? Сохранить настройки?")
        if confirmed and not state["finished"]:
            state["finished"] = True
            self.root.after_cancel(timer)
        elif not state["finished"]:
            self.root.after_cancel(timer)
            restore()

    def watch_monitors(self):
        try:
            devices = tuple(sorted(d["device"] for d in enumerate_displays()))
            added = bool(set(devices) - set(self.known_devices))
            if devices != self.known_devices:
                self.known_devices = devices
                self.audit("connection", "active display devices: " + ",".join(devices))
                self.refresh()
                if added and self.auto_profile.get():
                    self.root.after(100, self.offer_profile)
        except Exception:
            pass
        finally:
            self.root.after(5000, self.watch_monitors)

    def offer_profile(self):
        try:
            current = position_snapshot(enumerate_displays())
            for name, profile in read_profiles().items():
                try:
                    from display_engine import validate
                    validate(profile, current)
                except (ValueError, KeyError, TypeError):
                    continue
                if messagebox.askyesno("Подключён монитор", "Применить профиль «" + name + "»?"):
                    self.apply_named_profile(name, profile)
                break
        except Exception as exc:
            messagebox.showerror("Профили", str(exc))

    def fix_cursor(self, side):
        try:
            current = enumerate_displays()
            proposed = arrange_side_by_side(current, side)
            if proposed == position_snapshot(current):
                messagebox.showinfo("Переход мыши", "Экраны уже стоят рядом. Проверьте, что включён режим «Расширить», а не «Дублировать».")
                return
            if not messagebox.askyesno("Переход мыши",
                    "Мониторы будут выстроены рядом. Курсор сможет переходить через общую границу. Продолжить?"):
                return
            # Uses the existing confirmed change path with timed rollback.
            self.apply_named_profile("Переход мыши", proposed)
        except ValueError as exc:
            messagebox.showwarning("Переход мыши", str(exc) +
                "\\nПроверьте Win+P → Расширить и нажмите «Обновить диагностику».")
        except Exception as exc:
            messagebox.showerror("Переход мыши", str(exc))

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
        self.audit("layout", "requested profile: " + name)
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
        lines += ["", "ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ"]
        if any("AQ32H3" in (d["monitor"] + " " + d["monitor_id"]).upper() for d in self.details):
            lines.append("AQ32H3 обнаружен в активном режиме Windows.")
        elif any("AQ32H3" in str(v).upper() for v in self.identifiers):
            lines.append("AQ32H3 обнаружен WMI, но привязка к активному видеовыходу не подтверждена.")
        else:
            lines.append("AQ32H3 не идентифицирован; имя может быть скрыто адаптером/драйвером.")
        lines.append("Активный видеорежим не подтверждает исправность HDMI/DP кабеля и изображения.")
        lines += ["", "ПОДСКАЗКА"]
        if count >= 2:
            lines.append("Два экрана активны в Windows. Если один чёрный, проверьте вход HDMI/DP, кабель и частоту обновления в параметрах дисплея.")
        else:
            lines.append("Расширенный рабочий стол пока не подтверждён. Проверьте HDMI/DP, вход Source на мониторе и нажмите «Расширить экраны».")
        self.write("\n".join(lines))
        self.audit("scan", "active=" + str(count) + "; displays=" + ",".join(d["device"] for d in self.details))
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
