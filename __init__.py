from .autotune_node import AutoTuneSampler
from .combo_to_string import ComboToString
from .float_to_string import FloatToString
from .int_to_string import IntToString
from .preset_architect import PresetArchitect
from .preset_builder import PresetBuilder

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "AutoTuneSampler": AutoTuneSampler,
    "ComboToString": ComboToString,
    "FloatToString": FloatToString,
    "IntToString": IntToString,
    "PresetArchitect": PresetArchitect,
    "PresetBuilder": PresetBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoTuneSampler": "AutoTune Sampler",
    "ComboToString": "COMBO to STRING",
    "FloatToString": "FLOAT to STRING",
    "IntToString": "INT to STRING",
    "PresetArchitect": "Preset Architect",
    "PresetBuilder": "Preset Builder",
}
