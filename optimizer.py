import json
import os
import random

import optuna
import torch
import numpy as np

import comfy.samplers
import comfy.sample
import comfy.utils
import nodes
from PIL import Image

from .scorer import AestheticScorer
from .db import save_trial
from .status import StatusCollector

# Suppress Optuna's verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)

_PROMPT_BANK_PATH = os.path.join(os.path.dirname(__file__), "prompt_bank.json")


def _load_prompt_bank() -> list[str]:
    with open(_PROMPT_BANK_PATH, "r") as f:
        return json.load(f)


def _detect_native_resolution(model, checkpoint_path: str) -> tuple[int, int]:
    """Detect the checkpoint's native resolution from model config or file size."""
    try:
        # Check model config for resolution hints
        if hasattr(model, "model_config") and hasattr(
            model.model_config, "unet_config"
        ):
            config = model.model_config.unet_config
            # SDXL models typically have context_dim=2048
            if isinstance(config, dict) and config.get("context_dim", 0) >= 2048:
                return (1024, 1024)
    except Exception:
        pass

    # Fallback: use file size heuristic
    try:
        file_size = os.path.getsize(checkpoint_path)
        if file_size > 2 * 1024 * 1024 * 1024:  # > 2GB
            return (1024, 1024)
    except Exception:
        pass

    return (512, 512)


def _encode_prompt(clip, text: str, seed: int):
    """Encode a text prompt using the CLIP model, returning conditioning."""
    tokens = clip.tokenize(text)
    output = clip.encode_from_tokens(tokens, return_pooled=True, return_dict=True)
    cond = output.pop("cond")
    return [[cond, output]]


def _empty_conditioning(clip):
    """Create empty negative conditioning."""
    return _encode_prompt(clip, "", 0)


def _generate_image(
    model,
    clip,
    vae,
    positive_cond,
    negative_cond,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: int,
    width: int,
    height: int,
) -> Image.Image | None:
    """Generate a single image and return it as a PIL Image."""
    try:
        # Create empty latent
        batch_size = 1
        latent = torch.zeros(
            [batch_size, 4, height // 8, width // 8],
            device=comfy.model_management.intermediate_device(),
        )
        latent_dict = {"samples": latent}

        # Sample
        sampler = comfy.samplers.KSampler(
            model,
            steps=steps,
            device=comfy.model_management.get_torch_device(),
            sampler=sampler_name,
            scheduler=scheduler,
            denoise=1.0,
        )

        samples = sampler.sample(
            noise=torch.randn_like(latent),
            positive=positive_cond,
            negative=negative_cond,
            cfg=cfg,
            latent_image=latent,
            start_step=None,
            last_step=None,
            force_full_denoise=True,
            denoise_mask=None,
            sigmas=None,
            callback=None,
            disable_pbar=True,
            seed=seed,
        )

        # Decode with VAE
        decoded = vae.decode(samples)

        # Convert to PIL - decoded is [B, H, W, C] float tensor in 0-1
        img_np = (decoded[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        return Image.fromarray(img_np)

    except Exception as e:
        print(f"[AutoTune] Image generation failed: {e}")
        return None


def run_optimization(
    model,
    clip,
    vae,
    checkpoint_path: str,
    checkpoint_hash: str,
    max_trials: int,
    prompts_per_trial: int,
    seed: int,
    top_k_verify: int,
    status: StatusCollector | None = None,
) -> dict:
    """Run the full Bayesian optimization pipeline.

    Returns a dict with keys: steps, cfg, sampler_name, scheduler, mean_score,
    native_resolution.
    """
    if status is None:
        status = StatusCollector(max_trials)

    prompt_bank = _load_prompt_bank()
    rng = random.Random(seed)
    scorer = AestheticScorer()
    scorer.load()

    all_sampler_names = comfy.samplers.KSampler.SAMPLERS
    all_schedulers = comfy.samplers.KSampler.SCHEDULERS

    # Pre-encode negative conditioning once
    negative_cond = _empty_conditioning(clip)

    # ------------------------------------------------------------------
    # Phase 1 — Coarse search at 256x256
    # ------------------------------------------------------------------
    status.log(f"Phase 1: Coarse search ({max_trials} trials at 256x256)")

    coarse_results = []

    def objective(trial: optuna.Trial) -> float:
        steps = trial.suggest_int("steps", 4, 50)
        cfg = trial.suggest_float("cfg", 1.0, 20.0)
        sampler_name = trial.suggest_categorical("sampler_name", all_sampler_names)
        scheduler = trial.suggest_categorical("scheduler", all_schedulers)

        # Select random prompts for this trial
        selected_prompts = rng.sample(
            prompt_bank, min(prompts_per_trial, len(prompt_bank))
        )

        scores = []
        for i, prompt_text in enumerate(selected_prompts):
            positive_cond = _encode_prompt(clip, prompt_text, seed)
            trial_seed = seed + trial.number * 1000 + i

            img = _generate_image(
                model,
                clip,
                vae,
                positive_cond,
                negative_cond,
                steps,
                cfg,
                sampler_name,
                scheduler,
                trial_seed,
                256,
                256,
            )

            if img is not None:
                try:
                    score = scorer.score(img)
                    scores.append(score)
                except Exception as e:
                    status.log(f"Scoring failed: {e}")

        if not scores:
            return 0.0

        mean_score = float(np.mean(scores))

        # Save trial to database
        save_trial(
            checkpoint_hash=checkpoint_hash,
            trial_number=trial.number,
            phase="coarse",
            steps=steps,
            cfg=cfg,
            sampler_name=sampler_name,
            scheduler=scheduler,
            mean_score=mean_score,
            individual_scores=scores,
            resolution="256x256",
        )

        coarse_results.append(
            {
                "trial_number": trial.number,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "mean_score": mean_score,
            }
        )

        status.trial_complete(
            trial.number,
            {"steps": steps, "cfg": cfg, "sampler_name": sampler_name, "scheduler": scheduler},
            mean_score,
        )

        return mean_score

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=seed),
    )
    study.optimize(objective, n_trials=max_trials, show_progress_bar=False)

    # Sort by score descending and pick top-k
    coarse_results.sort(key=lambda x: x["mean_score"], reverse=True)
    top_candidates = coarse_results[:top_k_verify]

    if not top_candidates:
        scorer.unload()
        status.log("ERROR: No valid trials completed. Cannot optimize.")
        raise RuntimeError("[AutoTune] No valid trials completed. Cannot optimize.")

    # ------------------------------------------------------------------
    # Phase 2 — Verify top-k at native resolution
    # ------------------------------------------------------------------
    native_w, native_h = _detect_native_resolution(model, checkpoint_path)
    native_res_str = f"{native_w}x{native_h}"
    status.log(
        f"Phase 2: Verifying top {len(top_candidates)} candidates "
        f"at {native_res_str}"
    )

    best_candidate = None
    best_score = -1.0

    for idx, candidate in enumerate(top_candidates):
        selected_prompts = rng.sample(
            prompt_bank, min(prompts_per_trial, len(prompt_bank))
        )

        scores = []
        for i, prompt_text in enumerate(selected_prompts):
            positive_cond = _encode_prompt(clip, prompt_text, seed)
            trial_seed = seed + 100000 + idx * 1000 + i

            try:
                img = _generate_image(
                    model,
                    clip,
                    vae,
                    positive_cond,
                    negative_cond,
                    candidate["steps"],
                    candidate["cfg"],
                    candidate["sampler_name"],
                    candidate["scheduler"],
                    trial_seed,
                    native_w,
                    native_h,
                )
            except torch.cuda.OutOfMemoryError:
                status.log(
                    "OOM during Phase 2 verification. "
                    "Decision: Falling back to coarse-phase winner."
                )
                scorer.unload()
                winner = coarse_results[0]
                status.log(
                    f"Final result (coarse fallback): steps={winner['steps']}, "
                    f"cfg={winner['cfg']:.2f}, sampler={winner['sampler_name']}, "
                    f"scheduler={winner['scheduler']}, score={winner['mean_score']:.4f}"
                )
                return {
                    "steps": winner["steps"],
                    "cfg": winner["cfg"],
                    "sampler_name": winner["sampler_name"],
                    "scheduler": winner["scheduler"],
                    "mean_score": winner["mean_score"],
                    "native_resolution": native_res_str,
                }

            if img is not None:
                try:
                    score = scorer.score(img)
                    scores.append(score)
                except Exception as e:
                    status.log(f"Scoring failed during verification: {e}")

        if scores:
            mean_score = float(np.mean(scores))
        else:
            mean_score = candidate["mean_score"]  # fallback to coarse score

        # Save verification trial
        save_trial(
            checkpoint_hash=checkpoint_hash,
            trial_number=candidate["trial_number"],
            phase="verify",
            steps=candidate["steps"],
            cfg=candidate["cfg"],
            sampler_name=candidate["sampler_name"],
            scheduler=candidate["scheduler"],
            mean_score=mean_score,
            individual_scores=scores,
            resolution=native_res_str,
        )

        status.log(
            f"Candidate {idx + 1}/{len(top_candidates)}: "
            f"steps={candidate['steps']}, cfg={candidate['cfg']:.2f}, "
            f"sampler={candidate['sampler_name']}, scheduler={candidate['scheduler']}, "
            f"score={mean_score:.4f}"
        )

        if mean_score > best_score:
            best_score = mean_score
            best_candidate = {
                "steps": candidate["steps"],
                "cfg": candidate["cfg"],
                "sampler_name": candidate["sampler_name"],
                "scheduler": candidate["scheduler"],
                "mean_score": mean_score,
                "native_resolution": native_res_str,
            }

    scorer.unload()

    # Handle edge case: all trials score nearly identical
    if coarse_results:
        score_range = coarse_results[0]["mean_score"] - coarse_results[-1]["mean_score"]
        if score_range < 0.1 and len(coarse_results) > 1:
            status.log(
                "WARNING: All trials scored nearly identically. "
                "Checkpoint may be insensitive to parameter changes. "
                "Decision: Returning fastest combo (lowest steps)."
            )
            # Pick lowest steps among top candidates
            top_candidates.sort(key=lambda x: x["steps"])
            fastest = top_candidates[0]
            best_candidate = {
                "steps": fastest["steps"],
                "cfg": fastest["cfg"],
                "sampler_name": fastest["sampler_name"],
                "scheduler": fastest["scheduler"],
                "mean_score": fastest["mean_score"],
                "native_resolution": native_res_str,
            }

    status.log(
        f"Optimization complete. Best result: steps={best_candidate['steps']}, "
        f"cfg={best_candidate['cfg']:.2f}, sampler={best_candidate['sampler_name']}, "
        f"scheduler={best_candidate['scheduler']}, score={best_candidate['mean_score']:.4f}"
    )

    return best_candidate
