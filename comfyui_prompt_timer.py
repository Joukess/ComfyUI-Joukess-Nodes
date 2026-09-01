"""
Prompt Timer — ComfyUI custom node pair
----------------------------------------
Дає РЕАЛЬНИЙ вихід (не просто дисплей): СЕРЕДНІЙ АРИФМЕТИЧНИЙ час
виконання УСІХ попередніх прогонів workflow, який можна тягнути далі
по графу (в filename_prefix, в текст, куди завгодно).

Встановлення:
    Покласти цей файл у  ComfyUI/custom_nodes/comfyui_prompt_timer.py
    і перезапустити ComfyUI. Окрема папка/`__init__.py` не потрібні.

Як користуватись:
    1. "Prompt Timer — Get Average" постав будь-де на початку графа,
       нічого в неї заводити не треба (справжня СТАРТОВА нода).
       Вихід avg_seconds — це FLOAT, округлений до сотих: середнє
       арифметичне тривалості УСІХ прогонів, що завершились до цього.
       Обов'язково підключи вихід ХОЧ КУДИСЬ, інакше ComfyUI взагалі
       не виконає ноду (не пов'язана з жодним output-вузлом).
    2. "Prompt Timer — Save Current" постав ЯКОМОГА ПІЗНІШЕ в графі.
       Це справжня КІНЦЕВА нода (OUTPUT_NODE=True) — досить завести
       в неї будь-що (наприклад фінальний IMAGE) і далі нікуди не
       тягнути, вона виконається сама. Якщо хочеш — можеш і далі
       провести "any" на вихід (наприклад в Save Image), це теж
       працює, вихід просто повертає вхід без змін (passthrough).
       Головне — щоб вхід приходив від чогось, що виконується
       останнім у твоєму графі, бо саме в цей момент рахується час.

Логіка:
    Get Average, запускаючись, читає total_duration і count з
    json-файлу, рахує total_duration / count (середнє за ВСІ минулі
    прогони) і одразу перезаписує start_time на "зараз". Save Current,
    запускаючись пізніше в тому ж прогоні, рахує (зараз - start_time),
    додає цю тривалість до total_duration і збільшує count на 1 —
    тобто поточний прогін увійде в середнє вже на НАСТУПНОМУ запуску.

    Стан зберігається в execution_timer_state.json поруч із цим файлом,
    тож переживає перезапуск ComfyUI.
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
    "SecondsToHumanString": SecondsToHumanString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptTimerStart": "⏱ Prompt Timer — Get Average",
    "PromptTimerStop": "⏱ Prompt Timer — Save Current",
    "SecondsToHumanString": "⏱ Seconds → Human String",
}
