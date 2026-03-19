import os

import comfy.samplers
import folder_paths

from . import db
from .hasher import fast_checkpoint_hash, checkpoint_display_name
from .optimizer import run_optimization


class AutoTuneSampler:
    """ComfyUI node that uses Bayesian optimization to find the best sampling
    parameters for a given checkpoint model."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "mode": (["optimize", "lookup"],),
                "max_trials": (
                    "INT",
                    {"default": 40, "min": 1, "max": 200, "step": 1},
                ),
                "prompts_per_trial": (
                    "INT",
                    {"default": 5, "min": 1, "max": 20, "step": 1},
                ),
                "seed": (
                    "INT",
                    {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "top_k_verify": (
                    "INT",
                    {"default": 3, "min": 1, "max": 10, "step": 1},
                ),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", comfy.samplers.KSampler.SAMPLERS, comfy.samplers.KSampler.SCHEDULERS)
    RETURN_NAMES = ("steps", "cfg", "sampler_name", "scheduler")
    FUNCTION = "execute"
    CATEGORY = "sampling"

    def execute(
        self,
        model,
        clip,
        vae,
        mode: str,
        max_trials: int,
        prompts_per_trial: int,
        seed: int,
        top_k_verify: int,
    ):
        db.init_db()

        # Find the checkpoint file path
        checkpoint_path = self._find_checkpoint_path(model)
        ckpt_hash = fast_checkpoint_hash(checkpoint_path)
        ckpt_name = checkpoint_display_name(checkpoint_path)

        print(f"[AutoTune] Checkpoint: {ckpt_name} (hash: {ckpt_hash[:16]}...)")

        # Check cache
        cached = db.get_cached_params(ckpt_hash)

        if mode == "lookup":
            if cached is None:
                raise RuntimeError(
                    f"[AutoTune] No cached results found for {ckpt_name}. "
                    f"Run with mode='optimize' first."
                )
            print(f"[AutoTune] Returning cached results for {ckpt_name}")
            return (
                cached["steps"],
                cached["cfg"],
                cached["sampler_name"],
                cached["scheduler"],
            )

        # mode == "optimize"
        if cached is not None:
            print(
                f"[AutoTune] Cached results exist for {ckpt_name}, "
                f"but proceeding with re-optimization."
            )

        result = run_optimization(
            model=model,
            clip=clip,
            vae=vae,
            checkpoint_path=checkpoint_path,
            checkpoint_hash=ckpt_hash,
            max_trials=max_trials,
            prompts_per_trial=prompts_per_trial,
            seed=seed,
            top_k_verify=top_k_verify,
        )

        # Phase 3 — Persist
        db.save_optimal_params(
            checkpoint_hash=ckpt_hash,
            checkpoint_name=ckpt_name,
            steps=result["steps"],
            cfg=result["cfg"],
            sampler_name=result["sampler_name"],
            scheduler=result["scheduler"],
            mean_score=result["mean_score"],
            native_resolution=result["native_resolution"],
            trials_run=max_trials,
            prompts_per_trial=prompts_per_trial,
        )

        print(
            f"[AutoTune] Optimization complete for {ckpt_name}:\n"
            f"  steps={result['steps']}, cfg={result['cfg']:.2f}, "
            f"sampler={result['sampler_name']}, scheduler={result['scheduler']}, "
            f"score={result['mean_score']:.4f}"
        )

        return (
            result["steps"],
            result["cfg"],
            result["sampler_name"],
            result["scheduler"],
        )

    @staticmethod
    def _find_checkpoint_path(model) -> str:
        """Resolve the file path of the loaded checkpoint model."""
        # Try to get the path from model metadata
        if hasattr(model, "model") and hasattr(model.model, "model_config"):
            config = model.model.model_config
            if hasattr(config, "unet_config") and isinstance(
                config.unet_config, dict
            ):
                path = config.unet_config.get("model_path")
                if path and os.path.isfile(path):
                    return path

        # Search through ComfyUI's known checkpoint directories
        ckpt_dirs = folder_paths.get_folder_paths("checkpoints")
        for d in ckpt_dirs:
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.endswith((".safetensors", ".ckpt", ".pt", ".pth", ".bin")):
                        return os.path.join(root, f)

        raise RuntimeError(
            "[AutoTune] Could not determine checkpoint file path. "
            "Ensure a checkpoint model is loaded."
        )
