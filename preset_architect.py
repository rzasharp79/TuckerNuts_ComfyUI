import json
import os

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
    """Return sorted preset names with 'New Preset' sentinel at the end."""
    names = sorted(_load_presets().keys())
    return names + ["New Preset"] if names else ["New Preset"]


class PresetArchitect:
    """ComfyUI node for saving, loading, and deleting sampling parameter presets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": (_preset_names(),),
                "new_preset_name": ("STRING", {"default": ""}),
                "mode": (["use", "save", "delete"],),
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

    RETURN_TYPES = (
        "STRING",
        "INT",
        "FLOAT",
        "INT",
        comfy.samplers.KSampler.SAMPLERS,
        comfy.samplers.KSampler.SCHEDULERS,
        "STRING",
        "STRING",
    )
    RETURN_NAMES = (
        "checkpoint",
        "steps",
        "cfg",
        "clip_skip",
        "sampler_name",
        "scheduler",
        "positive_mod",
        "negative_mod",
    )
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

        if mode == "use":
            if preset_name == "New Preset" or preset_name not in presets:
                raise RuntimeError(
                    f"[PresetArchitect] No preset selected to use. "
                    f"Select an existing preset or save one first."
                )
            p = presets[preset_name]
            print(f"[PresetArchitect] Loaded preset: {preset_name}")
            return (
                p["checkpoint"],
                p["steps"],
                p["cfg"],
                p["clip_skip"],
                p["sampler"],
                p["scheduler"],
                p["positive_mod"],
                p["negative_mod"],
            )

        elif mode == "save":
            effective_name = (
                new_preset_name.strip()
                if preset_name == "New Preset"
                else preset_name
            )
            if not effective_name:
                raise RuntimeError(
                    "[PresetArchitect] Preset name cannot be empty. "
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
            print(f"[PresetArchitect] Saved preset: {effective_name}")
            return (
                checkpoint,
                steps,
                round(cfg, 2),
                clip_skip,
                sampler,
                scheduler,
                positive_mod,
                negative_mod,
            )

        elif mode == "delete":
            if preset_name == "New Preset" or preset_name not in presets:
                raise RuntimeError(
                    f"[PresetArchitect] Cannot delete: preset '{preset_name}' not found."
                )
            del presets[preset_name]
            _save_presets(presets)
            print(f"[PresetArchitect] Deleted preset: {preset_name}")
            return (
                "",
                20,
                7.50,
                -1,
                comfy.samplers.KSampler.SAMPLERS[0],
                comfy.samplers.KSampler.SCHEDULERS[0],
                "",
                "",
            )

        raise RuntimeError(f"[PresetArchitect] Unknown mode: {mode}")
