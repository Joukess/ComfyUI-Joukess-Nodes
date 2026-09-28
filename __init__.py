"""
ComfyUI-Joukess-Nodes
=====================
Набір кастомних нод для ComfyUI від Joukess.

Встановлення:
    git clone https://github.com/Joukess/ComfyUI-Promt-Timer.git
    у папку ComfyUI/custom_nodes/ і перезапустити ComfyUI.
"""

from .nodes.prompt_timer import (
    NODE_CLASS_MAPPINGS as _timer_nodes,
    NODE_DISPLAY_NAME_MAPPINGS as _timer_names,
)
from .nodes.step_indices import (
    NODE_CLASS_MAPPINGS as _step_nodes,
    NODE_DISPLAY_NAME_MAPPINGS as _step_names,
)
from .nodes.unzip_to_input import (
    NODE_CLASS_MAPPINGS as _unzip_nodes,
    NODE_DISPLAY_NAME_MAPPINGS as _unzip_names,
)
from .nodes.always_execute import (
    NODE_CLASS_MAPPINGS as _always_nodes,
    NODE_DISPLAY_NAME_MAPPINGS as _always_names,
)

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for _mappings in (_timer_nodes, _step_nodes, _unzip_nodes, _always_nodes):
    NODE_CLASS_MAPPINGS.update(_mappings)

for _mappings in (_timer_names, _step_names, _unzip_names, _always_names):
    NODE_DISPLAY_NAME_MAPPINGS.update(_mappings)


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
