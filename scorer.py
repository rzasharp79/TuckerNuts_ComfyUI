import os
import threading

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# URL for the LAION aesthetic predictor v2.5 weights
_WEIGHTS_URL = (
    "https://github.com/christophschuhmann/improved-aesthetic-predictor/"
    "raw/main/sac%2Blogos%2Bava1-l14-linearMSE.pth"
)
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
_WEIGHTS_FILE = os.path.join(_MODELS_DIR, "sa_0_4_vit_l_14_linear.pth")


class AestheticMLP(nn.Module):
    """Lightweight MLP head that maps CLIP ViT-L/14 embeddings to an aesthetic score."""

    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(768, 1024),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.Dropout(0.1),
            nn.Linear(64, 16),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.layers(x)


class AestheticScorer:
    """Scores images using the LAION aesthetic predictor v2.5.

    Loads a CLIP ViT-L/14 model for embeddings and an MLP head for scoring.
    Runs on CPU to avoid VRAM pressure during optimization.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._mlp: AestheticMLP | None = None
        self._clip_model = None
        self._clip_preprocess = None
        self._device = torch.device("cpu")

    def _ensure_weights(self):
        if os.path.isfile(_WEIGHTS_FILE):
            return
        os.makedirs(_MODELS_DIR, exist_ok=True)
        print(f"[AutoTune] Downloading aesthetic predictor weights to {_WEIGHTS_FILE}")
        try:
            import urllib.request
            urllib.request.urlretrieve(_WEIGHTS_URL, _WEIGHTS_FILE)
        except Exception as e:
            raise RuntimeError(
                f"Failed to download aesthetic predictor weights from {_WEIGHTS_URL}. "
                f"Please download manually and place at {_WEIGHTS_FILE}. Error: {e}"
            )

    def load(self):
        """Load the CLIP model and aesthetic MLP."""
        with self._lock:
            if self._mlp is not None:
                return

            self._ensure_weights()

            # Load CLIP ViT-L/14 for image embeddings
            try:
                import open_clip

                self._clip_model, _, self._clip_preprocess = (
                    open_clip.create_model_and_transforms(
                        "ViT-L-14", pretrained="openai"
                    )
                )
            except ImportError:
                try:
                    import clip

                    self._clip_model, self._clip_preprocess = clip.load(
                        "ViT-L/14", device="cpu"
                    )
                except ImportError:
                    from transformers import CLIPModel, CLIPProcessor

                    self._clip_model = CLIPModel.from_pretrained(
                        "openai/clip-vit-large-patch14"
                    )
                    self._clip_preprocess = CLIPProcessor.from_pretrained(
                        "openai/clip-vit-large-patch14"
                    )

            self._clip_model = self._clip_model.to(self._device)
            self._clip_model.eval()

            # Load the aesthetic MLP head
            self._mlp = AestheticMLP()
            state_dict = torch.load(_WEIGHTS_FILE, map_location=self._device)
            self._mlp.load_state_dict(state_dict)
            self._mlp.to(self._device)
            self._mlp.eval()

    def score(self, image: Image.Image) -> float:
        """Score a single PIL image. Returns a float typically in range 1-10."""
        if self._mlp is None:
            raise RuntimeError("Scorer not loaded. Call load() first.")

        with torch.no_grad():
            # Handle different CLIP backends
            if hasattr(self._clip_preprocess, "__call__") and not hasattr(
                self._clip_preprocess, "feature_extractor"
            ):
                # open_clip or clip style
                image_tensor = self._clip_preprocess(image).unsqueeze(0).to(self._device)
                features = self._clip_model.encode_image(image_tensor)
            else:
                # transformers style
                inputs = self._clip_preprocess(images=image, return_tensors="pt")
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                features = self._clip_model.get_image_features(**inputs)

            # Normalize
            features = features / features.norm(dim=-1, keepdim=True)
            score = self._mlp(features.float())
            return score.item()

    def unload(self):
        """Free all models from memory."""
        with self._lock:
            self._mlp = None
            self._clip_model = None
            self._clip_preprocess = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
