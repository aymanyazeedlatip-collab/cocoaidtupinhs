from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, brier_score_loss, confusion_matrix, f1_score, log_loss,
    mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.generate_data import create_synthetic_dataset

DATA_PATH = ROOT / "data" / "synthetic" / "coconut_farm_years.csv"
ARTIFACT_DIR = ROOT / "artifacts" / "models"
CARD_DIR = ROOT / "artifacts" / "model_cards"

PRODUCTION_FEATURES = [
    "farm_area_hectares", "productive_trees", "aging_trees", "stressed_trees", "infested_trees", "recovering_trees",
    "annual_rainfall_mm", "mean_temperature_c", "relative_humidity_percent", "drought_exposure", "weather_severity",
    "soil_ph", "nitrogen_index", "phosphorus_index", "potassium_index", "suitability_score", "pest_probability", "variety", "intervention"
]
PEST_FEATURES = [
    "annual_rainfall_mm", "mean_temperature_c", "relative_humidity_percent", "average_tree_age",
    "yellowing", "crown_decline", "frond_cuts", "visible_scale_insects", "rhinoceros_beetle_damage",
    "premature_nut_fall", "nearby_reports", "symptom_severity", "pest_control"
]
SUITABILITY_FEATURES = [
    "annual_rainfall_mm", "mean_temperature_c", "relative_humidity_percent", "elevation_m", "slope_degrees",
    "soil_ph", "nitrogen_index", "phosphorus_index", "potassium_index", "drainage_index", "drought_exposure", "typhoon_exposure"
]


def _split(df: pd.DataFrame):
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.22, random_state=42)
    train_idx, test_idx = next(splitter.split(df, groups=df["farm_id"]))
    return df.iloc[train_idx].copy(), df.iloc[test_idx].copy()


def _preprocessor(features: list[str], df: pd.DataFrame) -> ColumnTransformer:
    categorical = [f for f in features if df[f].dtype == object]
    numeric = [f for f in features if f not in categorical]
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ], remainder="drop")


def train_all() -> dict:
    if not DATA_PATH.exists():
        create_synthetic_dataset(DATA_PATH)
    df = pd.read_csv(DATA_PATH)
    train, test = _split(df)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    prod = Pipeline([
        ("prep", _preprocessor(PRODUCTION_FEATURES, df)),
        ("model", HistGradientBoostingRegressor(max_iter=220, learning_rate=0.06, max_leaf_nodes=25, random_state=42)),
    ])
    prod.fit(train[PRODUCTION_FEATURES], train["annual_production_tons"])
    pred = prod.predict(test[PRODUCTION_FEATURES])
    prod_metrics = {
        "mae": float(mean_absolute_error(test.annual_production_tons, pred)),
        "rmse": float(np.sqrt(mean_squared_error(test.annual_production_tons, pred))),
        "r2": float(r2_score(test.annual_production_tons, pred)),
    }
    joblib.dump({"pipeline": prod, "features": PRODUCTION_FEATURES, "version": "production-synthetic-1.0"}, ARTIFACT_DIR / "production_model.joblib")
    report["production"] = prod_metrics

    pest = Pipeline([
        ("prep", _preprocessor(PEST_FEATURES, df)),
        ("model", HistGradientBoostingClassifier(max_iter=180, learning_rate=0.07, max_leaf_nodes=21, random_state=42)),
    ])
    pest.fit(train[PEST_FEATURES], train["pest_outcome"])
    proba = pest.predict_proba(test[PEST_FEATURES])[:, 1]
    cls = (proba >= 0.5).astype(int)
    pest_metrics = {
        "accuracy": float(accuracy_score(test.pest_outcome, cls)),
        "precision": float(precision_score(test.pest_outcome, cls, zero_division=0)),
        "recall": float(recall_score(test.pest_outcome, cls, zero_division=0)),
        "f1": float(f1_score(test.pest_outcome, cls, zero_division=0)),
        "roc_auc": float(roc_auc_score(test.pest_outcome, proba)),
        "brier": float(brier_score_loss(test.pest_outcome, proba)),
        "log_loss": float(log_loss(test.pest_outcome, proba)),
        "confusion_matrix": confusion_matrix(test.pest_outcome, cls).tolist(),
    }
    joblib.dump({"pipeline": pest, "features": PEST_FEATURES, "version": "pest-synthetic-1.0"}, ARTIFACT_DIR / "pest_model.joblib")
    report["pest"] = pest_metrics

    suitability = Pipeline([
        ("prep", _preprocessor(SUITABILITY_FEATURES, df)),
        ("model", RandomForestRegressor(n_estimators=180, max_depth=12, min_samples_leaf=3, random_state=42, n_jobs=1)),
    ])
    suitability.fit(train[SUITABILITY_FEATURES], train["suitability_score"])
    spred = suitability.predict(test[SUITABILITY_FEATURES])
    suitability_metrics = {
        "mae": float(mean_absolute_error(test.suitability_score, spred)),
        "rmse": float(np.sqrt(mean_squared_error(test.suitability_score, spred))),
        "r2": float(r2_score(test.suitability_score, spred)),
    }
    joblib.dump({"pipeline": suitability, "features": SUITABILITY_FEATURES, "version": "suitability-synthetic-1.0"}, ARTIFACT_DIR / "suitability_model.joblib")
    report["suitability"] = suitability_metrics

    statement = "The model learned the relationships encoded in the synthetic reference-based development dataset. Real-world validation remains required."
    for name, metrics in report.items():
        (CARD_DIR / f"{name.upper()}_MODEL_CARD.json").write_text(json.dumps({
            "model": name, "version": f"{name}-synthetic-1.0", "data_source_type": "synthetic_reference_based", "metrics": metrics,
            "statement": statement, "training_rows": len(train), "test_rows": len(test),
            "split": "grouped by synthetic farm ID", "random_seed": 42,
        }, indent=2), encoding="utf-8")
    (ROOT / "data" / "metadata" / "MODEL_EVALUATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(train_all(), indent=2))
