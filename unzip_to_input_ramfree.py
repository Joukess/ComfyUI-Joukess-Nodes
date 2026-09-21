"""
UnzipToInput (RAM-free) — модифікований форк ноди UnzipToInput
з пакету hmwl/ComfyUI_zip.
----------------------------------------------------------------
Відмінності від оригіналу:
    - НЕ відкриває кожну розпаковану картинку через PIL.Image.open()
      і НЕ пакує її в tensor. Саме цей крок в оригіналі забивав RAM
      усього сервера (не тільки самого ComfyUI-процесу), якщо в zip
      були сотні зображень — кожне читалось, декодувалось і лежало
      в images_list цілим float32-масивом аж до кінця виконання ноди.
    - Робить рівно те саме розпакування в input/ (та ж логіка з
      __MACOSX/, cp437-декодуванням імен, підтримкою URL замість
      локального шляху), але повертає ТІЛЬКИ folder (STRING).
      Виходу images більше немає — він і не був потрібен.
    - torch / numpy / PIL більше не імпортуються й не потрібні.

Встановлення:
    Покласти цей файл у ComfyUI/custom_nodes/unzip_to_input_ramfree.py
    і перезапустити ComfyUI. Окрема папка/__init__.py не потрібні —
    так само, як з comfyui_prompt_timer.py.

    NODE_CLASS_MAPPINGS ключ лишився "UnzipToInput" (як в оригіналі),
    тож старі workflow, що вже використовують цю ноду, продовжать
    працювати без змін — просто підвантажиться ця версія замість
    оригінального пакету hmwl/ComfyUI_zip (який більше не потрібно
    ставити поруч, інакше буде конфлікт реєстрації одного й того ж
    імені ноди між двома різними custom_nodes-файлами).
"""

import os
import time
import shutil
import zipfile
import urllib.request
from urllib.parse import urlparse

import folder_paths


class UnzipToInput:
    def __init__(self):
        self.output_dir = folder_paths.get_input_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "zip_path": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder",)
    FUNCTION = "unzip_process"
    CATEGORY = "comfyui_zip"

    def download_file(self, url, save_path):
        urllib.request.urlretrieve(url, save_path)

    def is_image_file(self, filename):
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
        return os.path.splitext(filename.lower())[1] in image_extensions

    def unzip_process(self, zip_path):
        timestamp = str(int(time.time()))
        extract_dir = os.path.join(self.output_dir, f"unzip_{timestamp}")
        os.makedirs(extract_dir, exist_ok=True)

        # URL чи локальний шлях
        if zip_path.startswith(('http://', 'https://')):
            parsed_url = urlparse(zip_path)
            zip_filename = os.path.basename(parsed_url.path)
            temp_zip = os.path.join(extract_dir, zip_filename)
            self.download_file(zip_path, temp_zip)
            zip_path = temp_zip

        # Розпакування, з обробкою __MACOSX та кирилиці/юнікоду в іменах
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            name_list = zip_ref.namelist()

            filtered_names = [
                name for name in name_list
                if not name.startswith('__MACOSX/') and not name.startswith('._')
            ]

            for name in filtered_names:
                try:
                    unicode_name = name.encode('cp437').decode('utf-8')
                except Exception:
                    unicode_name = name

                extracted_path = os.path.join(extract_dir, unicode_name)
                os.makedirs(os.path.dirname(extracted_path), exist_ok=True)

                with zip_ref.open(name) as source, open(extracted_path, 'wb') as target:
                    shutil.copyfileobj(source, target)

        # Тільки перевірка що картинки є (по розширенню, без Image.open) —
        # це і є заміна колишнього "читання й пакування в тензори"
        has_images = False
        for root, _, files in os.walk(extract_dir):
            if any(self.is_image_file(f) for f in files):
                has_images = True
                break

        if not has_images:
            raise ValueError("No image files found in ZIP archive")

        folder_name = os.path.basename(extract_dir)
        return (folder_name,)


NODE_CLASS_MAPPINGS = {
    "UnzipToInput": UnzipToInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UnzipToInput": "Unzip To Input (RAM-free)",
}
