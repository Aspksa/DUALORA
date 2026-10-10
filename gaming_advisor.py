"""Gaming display analysis. OS refresh rate is not rendered game FPS."""
from __future__ import annotations

def assess_display(display, modes):
    hz = int(display["hz"])
    width = int(display["width"])
    height = int(display["height"])
    max_hz = max((int(m["hz"]) for m in modes), default=hz)
    matching_hz = max((int(m["hz"]) for m in modes
                       if int(m["width"]) == width and int(m["height"]) == height),
                      default=hz)
    tips = []
    if matching_hz > hz:
        tips.append(f"Для текущего разрешения Windows предлагает {matching_hz} Гц вместо {hz} Гц.")
    elif max_hz > hz:
        tips.append(f"До {max_hz} Гц доступно только в других режимах; проверьте разрешение и кабель.")
    else:
        tips.append(f"Активная частота: {hz} Гц; более высокая не обнаружена.")
    tips.extend([
        "FPS игры зависит от видеокарты, процессора и настроек игры. Герцовка сама по себе FPS не увеличивает.",
        "Проверьте Game Mode Windows и питание ноутбука; при игре от батареи производительность может снижаться.",
        "Проверьте частоту в расширенных параметрах дисплея и V-Sync / лимит кадров в игре.",
        "G-Sync / FreeSync / VRR нельзя достоверно определить только из списка видеорежимов. Проверьте драйвер GPU, OSD монитора и настройки Windows.",
        "HDMI/DP, порт ноутбука и кабель должны поддерживать выбранный режим.",
    ])
    return {"device": str(display["device"]), "resolution": f"{width}x{height}",
            "current_hz": hz, "max_available_hz": max_hz,
            "max_at_current_resolution": matching_hz,
            "vrr_status": "не проверено", "tips": tips}
