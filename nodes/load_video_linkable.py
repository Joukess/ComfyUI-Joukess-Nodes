"""
Load Video (linkable) — вбудована нода LoadVideo, але з підтримкою підключеного `file`.

Проблема вбудованої ноди: коли поле `file` підключене до іншої ноди (наприклад,
рядок з "Text Load Line From File"), під час валідації графа значення ще невідоме,
і в VALIDATE_INPUTS приходить file=None. Далі folder_paths.exists_annotated_filepath(None)
викликає None.endswith(...) і ми бачимо:
    Validation failed: 'NoneType' object has no attribute 'endswith'

Ця нода робить те саме, що й вбудована (той самий тип VIDEO, upload-віджет, превʼю),
але пропускає перевірку, якщо file ще невідомий. Справжня перевірка існування файлу
відбувається у load_video, коли рядок уже відомий.

Обмеження: файл має лежати в ComfyUI/input (підпапки дозволені, наприклад "sub/a.mp4").
Абсолютні шляхи блокуються захистом ComfyUI від path traversal.
"""

import os

import folder_paths


def _video_from_file(path):
    # Нові версії ComfyUI
    try:
        from comfy_api.latest import InputImpl

        return InputImpl.VideoFromFile(path)
    except Exception:
        # Старіші версії
        from comfy_api.input_impl import VideoFromFile

        return VideoFromFile(path)


def _preview(file, video):
    """Превʼю у вузлі. Використовуємо хелпер вбудованої ноди (щоб Trim/Crop
    могли перевикористати превʼю), а якщо його немає - формуємо вручну."""
    try:
        from comfy_extras.nodes_video import preview_input_video

        return preview_input_video(file, video).as_dict()
    except Exception:
        name, _ = folder_paths.annotated_filepath(file)
        subfolder, _, filename = name.replace("\\", "/").rpartition("/")
        return {
            "images": [{"filename": filename, "subfolder": subfolder, "type": "input"}],
            "animated": (True,),
        }


class LoadVideoLinkable:
    """Load Video, у якого поле `file` можна підключати до інших нод."""

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f
            for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        ]
        files = folder_paths.filter_files_content_types(files, ["video"])
        return {"required": {"file": (sorted(files), {"video_upload": True})}}

    RETURN_TYPES = ("VIDEO",)
    FUNCTION = "load_video"
    CATEGORY = "video"
    HAS_INTERMEDIATE_OUTPUT = True

    def load_video(self, file):
        if not file or not folder_paths.exists_annotated_filepath(file):
            raise ValueError(
                f"Invalid video file: {file!r} (file must be inside the ComfyUI input folder)"
            )
        video = _video_from_file(folder_paths.get_annotated_filepath(file))
        return {"ui": _preview(file, video), "result": (video,)}

    @classmethod
    def IS_CHANGED(cls, file):
        try:
            return os.path.getmtime(folder_paths.get_annotated_filepath(file))
        except Exception:
            return "missing"

    @classmethod
    def VALIDATE_INPUTS(cls, file=None):
        # Головний фікс: якщо `file` підключено, під час валідації він None.
        if file is None:
            return True
        if not folder_paths.exists_annotated_filepath(file):
            return f"Invalid video file: {file}"
        return True


NODE_CLASS_MAPPINGS = {
    "JoukessLoadVideoLinkable": LoadVideoLinkable,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JoukessLoadVideoLinkable": "Load Video (linkable)",
}
