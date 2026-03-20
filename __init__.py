from .autotune_node import AutoTuneSampler
from .preset_architect import PresetArchitect
from .preset_builder import PresetBuilder

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "AutoTuneSampler": AutoTuneSampler,
    "PresetArchitect": PresetArchitect,
    "PresetBuilder": PresetBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoTuneSampler": "AutoTune Sampler",
    "PresetArchitect": "Preset Architect",
    "PresetBuilder": "Preset Builder",
}
