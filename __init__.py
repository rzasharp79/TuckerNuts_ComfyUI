from .autotune_node import AutoTuneSampler
from .preset_architect import PresetArchitect

NODE_CLASS_MAPPINGS = {
    "AutoTuneSampler": AutoTuneSampler,
    "PresetArchitect": PresetArchitect,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoTuneSampler": "AutoTune Sampler",
    "PresetArchitect": "Preset Architect",
}
