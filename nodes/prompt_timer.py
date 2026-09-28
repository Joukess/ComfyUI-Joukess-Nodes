"""
Prompt Timer — набір нод для вимірювання часу виконання workflow.

Ноди:
    - PromptTimerAverage  (mode: Start / End) — середній час усіх прогонів
    - PromptTimerCurrent  (mode: Start / End) — час поточного прогону
    - SecondsToHumanString — INT (секунди) → людино-зрозумілий STRING
"""

import time
import json
import os
import math

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "execution_timer_state.json"
)


# "Будь-який тип" сокет, який приймає з'єднання від чого завгодно
# (стандартний трюк у ComfyUI-нодах типу Reroute / Anything Everywhere).
class AnyType(str):
    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False


any_type = AnyType("*")

# Стартові мітки часу зберігаються у пам'яті модуля,
# щоб файлові операції не потрапляли у вимір.
_average_start: float | None = None
_current_start: float | None = None


def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[PromptTimer] Не вдалось зберегти стан: {e}")


# Скидаємо статистику при запуску ComfyUI (імпорт модуля = старт сервера).
_save_state({})


class PromptTimerAverage:
    """Вимірює СЕРЕДНІЙ час виконання workflow по всіх прогонах.

    Режим Start — ставиться на початку графа:
        фіксує момент старту та повертає середній час попередніх прогонів.
    Режим End — ставиться в кінці графа:
        зберігає тривалість поточного прогону до статистики.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["Start", "End"],),
            },
            "optional": {
                "any": (any_type,),
            },
        }

    RETURN_TYPES = ("FLOAT", any_type)
    RETURN_NAMES = ("avg_seconds", "any")
    FUNCTION = "run"
    CATEGORY = "utils/timer"
    OUTPUT_NODE = True  # потрібно для режиму End, щоб нода завжди виконувалась

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # завжди виконувати заново, ніколи не брати з кешу
        return float("nan")

    def run(self, mode, any=None):
        global _average_start

        if mode == "Start":
            # Спочатку читаємо статистику (до старту відліку).
            state = _load_state()
            total = state.get("total_duration", 0.0)
            count = state.get("count", 0)
            avg_seconds = round(total / count, 2) if count > 0 else 0.0

            # Мітка часу — остання дія, щоб I/O не потрапляв у вимір.
            _average_start = time.perf_counter()

            return (avg_seconds, any)

        else:  # mode == "End"
            # Мітка часу — перша дія, щоб I/O не потрапляв у вимір.
            now = time.perf_counter()

            if _average_start is not None:
                duration = max(0.0, now - _average_start)
                state = _load_state()
                state["total_duration"] = state.get("total_duration", 0.0) + duration
                state["count"] = state.get("count", 0) + 1
                _save_state(state)
            else:
                state = _load_state()

            # Повертаємо оновлений середній час.
            total = state.get("total_duration", 0.0)
            count = state.get("count", 0)
            avg_seconds = round(total / count, 2) if count > 0 else 0.0

            return (avg_seconds, any)


class PromptTimerCurrent:
    """Вимірює час ПОТОЧНОГО прогону workflow.

    Режим Start — ставиться на початку графа:
        фіксує момент старту відліку.
    Режим End — ставиться в кінці графа:
        повертає тривалість поточного прогону у секундах.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["Start", "End"],),
            },
            "optional": {
                "any": (any_type,),
            },
        }

    RETURN_TYPES = ("STRING", any_type)
    RETURN_NAMES = ("elapsed_seconds", "any")
    FUNCTION = "run"
    CATEGORY = "utils/timer"
    OUTPUT_NODE = True  # потрібно для режиму End

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Завжди виконувати заново, ніколи не брати з кешу.
        return float("nan")

    def run(self, mode, any=None):
        global _current_start

        if mode == "Start":
            # perf_counter() — остання дія перед return.
            # Жодного файлового I/O, мінімальна похибка.
            _current_start = time.perf_counter()
            return ("0.00", any)

        # mode == "End"
        # perf_counter() — перша дія, щоб I/O не потрапляв у вимір.
        now = time.perf_counter()

        if _current_start is None:
            return ("0.00", any)

        elapsed = max(0.0, now - _current_start)
        _current_start = None
        return (f"{elapsed:.2f}", any)


class SecondsToHumanString:
    """INT (секунди) -> STRING зручного формату: 23s / 45m / 1h 12m / 2h.

    Округлення завжди в БІЛЬШУ сторону на рівні хвилин:
        < 60s          -> "{s}s"
        60s..3599s     -> хвилини = ceil(s/60); якщо вийшло 60 -> "1h"
        >= 3600s       -> години = s//3600, залишок -> хвилини = ceil(залишок/60);
                          якщо хвилини == 60 -> +1 година, 0 хвилин;
                          якщо хвилини == 0  -> "{h}h", інакше "{h}h {m}m"
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seconds": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("formatted",)
    FUNCTION = "run"
    CATEGORY = "utils/timer"

    def run(self, seconds):
        seconds = max(0, int(seconds))

        if seconds < 60:
            return (f"{seconds}s",)

        if seconds < 3600:
            minutes = math.ceil(seconds / 60)
            if minutes >= 60:
                return ("1h",)
            return (f"{minutes}m",)

        hours, remainder = divmod(seconds, 3600)
        minutes = math.ceil(remainder / 60)
        if minutes >= 60:
            hours += 1
            minutes = 0

        if minutes == 0:
            return (f"{hours}h",)
        return (f"{hours}h {minutes}m",)


NODE_CLASS_MAPPINGS = {
    "PromptTimerAverage": PromptTimerAverage,
    "PromptTimerCurrent": PromptTimerCurrent,
    "SecondsToHumanString": SecondsToHumanString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTimerAverage": "⏱ Prompt Timer Average",
    "PromptTimerCurrent": "⏱ Prompt Timer Current",
    "SecondsToHumanString": "⏱ Seconds → Human String",
}
