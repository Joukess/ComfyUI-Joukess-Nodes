"""
Always Execute — нода-прохідник, яка обходить кешування ComfyUI.

Пропускає будь-яке з'єднання через себе без змін, але завжди
позначається як "змінена", тому ComfyUI перевиконує її та все,
що стоїть після неї у графі.
"""


class AnyType(str):
    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False


any_type = AnyType("*")


class AlwaysExecute:
    """Пропускає вхід наскрізь, але обходить кешування ComfyUI.

    Все, що розташовано після цієї ноди у графі, гарантовано
    виконається заново при кожному запуску workflow.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {"optional": {"any": (any_type,)}}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("any",)
    FUNCTION = "run"
    CATEGORY = "utils"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(self, any=None):
        return (any,)


NODE_CLASS_MAPPINGS = {
    "AlwaysExecute": AlwaysExecute,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AlwaysExecute": "🔄 Always Execute",
}
