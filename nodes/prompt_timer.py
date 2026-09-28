"""
Prompt Timer — набір нод для вимірювання часу виконання workflow.

Ноди:
    - PromptTimerStart / PromptTimerStop — середній час усіх прогонів
    - PromptTimerStartCurrent / PromptTimerStopCurrent — час поточного прогону
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


class PromptTimerStart:
    """Виводить СЕРЕДНІЙ час усіх попередніх прогонів і фіксує старт поточного."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"optional": {"any": (any_type,)}}

    RETURN_TYPES = ("FLOAT", any_type)
    RETURN_NAMES = ("avg_seconds", "any")
    FUNCTION = "run"
    CATEGORY = "utils/timer"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # завжди виконувати заново, ніколи не брати з кешу
        return float("nan")

    def run(self, any=None):
        state = _load_state()
        total = state.get("total_duration", 0.0)
        count = state.get("count", 0)
        avg_seconds = round(total / count, 2) if count > 0 else 0.0

        state["start_time"] = time.time()
        _save_state(state)

        return (avg_seconds, any)


class PromptTimerStop:
    """Ставиться пізно в графі. Додає тривалість поточного прогону до статистики."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"any": (any_type,)}}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("any",)
    FUNCTION = "run"
    CATEGORY = "utils/timer"
    OUTPUT_NODE = True  # завжди виконується, навіть якщо вихід нікуди не веде

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(self, any):
        state = _load_state()
        start = state.get("start_time")
        if start is not None:
            duration = time.time() - start
            state["total_duration"] = state.get("total_duration", 0.0) + duration
            state["count"] = state.get("count", 0) + 1
            _save_state(state)
        return (any,)


class PromptTimerStartCurrent:
    """Починає відлік часу для ПОТОЧНОГО прогону графа."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"optional": {"any": (any_type,)}}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("any",)
    FUNCTION = "run"
    CATEGORY = "utils/timer"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Завжди виконувати заново, ніколи не брати з кешу.
        return float("nan")

    def run(self, any=None):
        state = _load_state()
        # perf_counter() краще підходить для вимірювання інтервалів,
        # бо він монотонний і не залежить від зміни системного годинника.
        state["current_run_start_time"] = time.perf_counter()
        _save_state(state)

        return (any,)


class PromptTimerStopCurrent:
    """Завершує поточний відлік і повертає його тривалість у секундах як STRING."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"any": (any_type,)}}

    RETURN_TYPES = ("STRING", any_type)
    RETURN_NAMES = ("elapsed_seconds", "any")
    FUNCTION = "run"
    CATEGORY = "utils/timer"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(self, any):
        state = _load_state()
        start = state.get("current_run_start_time")

        if start is None:
            # Немає старту — повертаємо однозначне значення замість помилки.
            elapsed_seconds = "0.00"
        else:
            elapsed = max(0.0, time.perf_counter() - float(start))
            elapsed_seconds = f"{elapsed:.2f}"

            # Прибираємо ключ після завершення, щоб старий старт
            # не міг випадково використатись у наступному прогоні.
            state.pop("current_run_start_time", None)
            _save_state(state)

        return (elapsed_seconds, any,)


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
    "PromptTimerStart": PromptTimerStart,
    "PromptTimerStop": PromptTimerStop,
    "PromptTimerStartCurrent": PromptTimerStartCurrent,
    "PromptTimerStopCurrent": PromptTimerStopCurrent,
    "SecondsToHumanString": SecondsToHumanString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTimerStart": "⏱ Prompt Timer — Get Average",
    "PromptTimerStop": "⏱ Prompt Timer — Save Current",
    "PromptTimerStartCurrent": "⏱ Prompt Timer — Start Current",
    "PromptTimerStopCurrent": "⏱ Prompt Timer — Get Current",
    "SecondsToHumanString": "⏱ Seconds → Human String",
}
