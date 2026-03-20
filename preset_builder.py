import json
import os

from aiohttp import web
from server import PromptServer

import comfy.samplers
import folder_paths

PRESETS_FILE = os.path.join(os.path.dirname(__file__), "presets.json")


def _load_presets() -> dict:
    """Load presets from JSON file. Returns empty dict if file missing or invalid."""
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_presets(data: dict) -> None:
    """Write presets dictionary to JSON file."""
    with open(PRESETS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _preset_names() -> list[str]:
    """Return sorted preset names with 'New Preset' sentinel at the start."""
    names = sorted(_load_presets().keys())
    return ["New Preset"] + names if names else ["New Preset"]


@PromptServer.instance.routes.get("/tuckernuts/presets")
async def get_presets(request):
    """API endpoint that returns all saved presets."""
    return web.json_response(_load_presets())


@PromptServer.instance.routes.get("/tuckernuts/preset/{name}")
async def get_preset(request):
    """API endpoint that returns a single preset by name."""
    name = request.match_info["name"]
    presets = _load_presets()
    if name not in presets:
        return web.json_response({"error": f"Preset '{name}' not found"}, status=404)
    return web.json_response(presets[name])


class PresetBuilder:
    """ComfyUI node for saving, editing, and deleting sampling parameter presets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": (_preset_names(),),
                "new_preset_name": ("STRING", {"default": ""}),
                "mode": (["save", "delete", "edit"],),
                "checkpoint": (folder_paths.get_filename_list("checkpoints"),),
                "steps": (
                    "INT",
                    {"default": 20, "min": 1, "max": 150, "step": 1},
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 7.50,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.01,
                        "round": 0.01,
                    },
                ),
                "clip_skip": (
                    "INT",
                    {"default": -1, "min": -3, "max": -1, "step": 1},
                ),
                "sampler": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "positive_mod": ("STRING", {"default": "", "multiline": True}),
                "negative_mod": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "TuckerNuts"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force re-evaluation so the preset dropdown stays current
        return float("NaN")

    def execute(
        self,
        preset_name,
        new_preset_name,
        mode,
        checkpoint,
        steps,
        cfg,
        clip_skip,
        sampler,
        scheduler,
        positive_mod,
        negative_mod,
    ):
        presets = _load_presets()

        if mode == "save":
            effective_name = (
                new_preset_name.strip()
                if preset_name == "New Preset"
                else preset_name
            )
            if not effective_name:
                raise RuntimeError(
                    "[PresetBuilder] Preset name cannot be empty. "
                    "Enter a name in 'new_preset_name' when using 'New Preset'."
                )

            presets[effective_name] = {
                "checkpoint": checkpoint,
                "steps": steps,
                "cfg": round(cfg, 2),
                "clip_skip": clip_skip,
                "sampler": sampler,
                "scheduler": scheduler,
                "positive_mod": positive_mod,
                "negative_mod": negative_mod,
            }
            _save_presets(presets)
            print(f"[PresetBuilder] Saved preset: {effective_name}")

        elif mode == "edit":
            if preset_name == "New Preset" or preset_name not in presets:
                raise RuntimeError(
                    f"[PresetBuilder] Cannot edit: preset '{preset_name}' not found. "
                    f"Select an existing preset to edit."
                )

            new_name = new_preset_name.strip()
            if new_name and new_name != preset_name:
                del presets[preset_name]
                presets[new_name] = {
                    "checkpoint": checkpoint,
                    "steps": steps,
                    "cfg": round(cfg, 2),
                    "clip_skip": clip_skip,
                    "sampler": sampler,
                    "scheduler": scheduler,
                    "positive_mod": positive_mod,
                    "negative_mod": negative_mod,
                }
                _save_presets(presets)
                print(f"[PresetBuilder] Renamed '{preset_name}' to '{new_name}' and updated values")
            else:
                presets[preset_name] = {
                    "checkpoint": checkpoint,
                    "steps": steps,
                    "cfg": round(cfg, 2),
                    "clip_skip": clip_skip,
                    "sampler": sampler,
                    "scheduler": scheduler,
                    "positive_mod": positive_mod,
                    "negative_mod": negative_mod,
                }
                _save_presets(presets)
                print(f"[PresetBuilder] Updated preset: {preset_name}")

        elif mode == "delete":
            if preset_name == "New Preset" or preset_name not in presets:
                raise RuntimeError(
                    f"[PresetBuilder] Cannot delete: preset '{preset_name}' not found."
                )
            del presets[preset_name]
            _save_presets(presets)
            print(f"[PresetBuilder] Deleted preset: {preset_name}")

        else:
            raise RuntimeError(f"[PresetBuilder] Unknown mode: {mode}")

        return {}
