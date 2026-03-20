from .autotune_node import AutoTuneSampler
from .int_to_string import IntToString
from .preset_architect import PresetArchitect
from .preset_builder import PresetBuilder

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "AutoTuneSampler": AutoTuneSampler,
    "IntToString": IntToString,
    "PresetArchitect": PresetArchitect,
    "PresetBuilder": PresetBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoTuneSampler": "AutoTune Sampler",
    "IntToString": "INT to STRING",
    "PresetArchitect": "Preset Architect",
    "PresetBuilder": "Preset Builder",
}
