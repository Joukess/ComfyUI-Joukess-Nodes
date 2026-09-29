class StepIndices:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "total": ("INT", {"default": 100, "min": 0, "max": 100000}),
            "step": ("INT", {"default": 24, "min": 1, "max": 10000}),
            "last_index": (["N", "N-1"], {"default": "N-1"}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("indices", "indices_comma", "count")
    FUNCTION = "run"
    CATEGORY = "utils"

    def run(self, total, step, last_index):
        last = total if last_index == "N" else max(total - 1, 0)
        idx = list(range(0, last, step)) + [last]
        return ("_".join(map(str, idx)), ",".join(map(str, idx)), len(idx))

NODE_CLASS_MAPPINGS = {"StepIndices": StepIndices}
NODE_DISPLAY_NAME_MAPPINGS = {"StepIndices": "Step Indices"}
