from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.registry import clear_model_cache, model_metadata, model_runtime_status


def models_ready() -> bool:
    clear_model_cache()
    metadata = model_metadata()
    return bool(metadata) and all(item["available"] for item in metadata.values())


if __name__ == "__main__":
    if models_ready():
        runtime = model_runtime_status()
        if runtime["compatible"]:
            print("Bundled model artifacts are available under the exact serialized runtime.")
        else:
            print("Bundled model artifacts loaded in legacy compatibility mode.")
            print(runtime["action"])
        raise SystemExit(0)
    print("Model artifacts are missing or incompatible with the installed scikit-learn version.")
    print("Retraining development models now...")
    from scripts.train_models import train_all

    train_all()
    if not models_ready():
        raise RuntimeError("Model retraining completed but artifacts still could not be loaded")
    print("Development models retrained successfully.")
