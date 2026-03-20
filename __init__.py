from .autotune_node import AutoTuneSampler
from .preset_builder import PresetBuilder

NODE_CLASS_MAPPINGS = {
    "AutoTuneSampler": AutoTuneSampler,
    "PresetBuilder": PresetBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoTuneSampler": "AutoTune Sampler",
    "PresetBuilder": "Preset Builder",
}
