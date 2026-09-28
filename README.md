# ComfyUI-Joukess-Nodes

A collection of utility custom nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by **Joukess**.

## Installation

### Via ComfyUI Manager (recommended)

Search for **Joukess Nodes** in ComfyUI Manager and click Install.

### Manual

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Joukess/ComfyUI-Promt-Timer.git
```

Restart ComfyUI.

## Nodes

### ⏱ Prompt Timer — Get Average

Returns the **average duration** (FLOAT, seconds) across all previous workflow executions. Place it early in your graph.

### ⏱ Prompt Timer — Save Current

Records the duration of the current run. Place it **as late as possible** in the graph (it's an `OUTPUT_NODE`).

### ⏱ Prompt Timer — Start Current

Starts a timer for the **current** run. Pair with *Get Current*.

### ⏱ Prompt Timer — Get Current

Stops the current timer and returns elapsed time as STRING. Pair with *Start Current*.

### ⏱ Seconds → Human String

Converts an INT (seconds) to a human-readable string: `23s`, `45m`, `1h 12m`, `2h`.

### Step Indices

Generates a list of evenly-spaced frame indices from `0` to `total` with a given `step`. Returns both a `_`-separated STRING and a count INT.

### Unzip To Input (RAM-free)

Extracts a ZIP archive (local path or URL) into ComfyUI's `input/` directory **without** loading images into RAM. A memory-efficient fork of `hmwl/ComfyUI_zip`.

## License

[MIT](LICENSE)
