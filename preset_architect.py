import comfy.samplers
import comfy.sd
import folder_paths

from .preset_builder import _load_presets


def _saved_preset_names() -> list[str]:
    """Return sorted preset names (only real presets, no sentinel)."""
    names = sorted(_load_presets().keys())
    return names if names else ["(none)"]


class PresetArchitect:
    """Read-only ComfyUI node that loads a saved preset and outputs its values."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": (_saved_preset_names(),),
            }
        }

    RETURN_TYPES = (
        "MODEL",
        "CLIP",
        "VAE",
        "INT",
        "FLOAT",
        "INT",
        comfy.samplers.KSampler.SAMPLERS,
        comfy.samplers.KSampler.SCHEDULERS,
        "STRING",
        "STRING",
    )
    RETURN_NAMES = (
        "MODEL",
        "CLIP",
        "VAE",
        "STEPS",
        "CFG",
        "CLIP_SKIP",
        "SAMPLER",
        "SCHEDULER",
        "POSITIVE_MOD",
        "NEGATIVE_MOD",
    )
    FUNCTION = "execute"
    CATEGORY = "TuckerNuts"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @staticmethod
    def _load_checkpoint(ckpt_name: str):
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        if ckpt_path is None:
            raise RuntimeError(
                f"[PresetArchitect] Checkpoint not found: {ckpt_name}"
            )
        out = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=True,
            output_clip=True,
        )
        return out[0], out[1], out[2]

    def execute(self, preset_name):
        presets = _load_presets()

        if preset_name not in presets:
            raise RuntimeError(
                f"[PresetArchitect] Preset '{preset_name}' not found. "
                f"Use the Preset Builder node to create one first."
            )

        p = presets[preset_name]
        model, clip, vae = self._load_checkpoint(p["checkpoint"])

        return (
            model,
            clip,
            vae,
            p["steps"],
            p["cfg"],
            p["clip_skip"],
            p["sampler"],
            p["scheduler"],
            p["positive_mod"],
            p["negative_mod"],
        )
