import pandas as pd
from app.core.config import settings
from scripts.generate_data import create_synthetic_dataset


def test_dataset_schema_and_constraints(tmp_path):
    path = create_synthetic_dataset(tmp_path / "small.csv", seed=123, farms=12, years_per_farm=3)
    df = pd.read_csv(path)
    required = {"record_id","farm_id","data_source_type","is_synthetic","generation_version","generation_seed","reference_group","created_at","quality_flag"}
    assert required.issubset(df.columns)
    assert (df.annual_rainfall_mm >= 0).all()
    assert df.pest_probability.between(0,1).all()
    states=["young_trees","productive_trees","aging_trees","stressed_trees","infested_trees","recovering_trees","dead_trees"]
    assert (df[states].sum(axis=1) == df.total_trees).all()


def test_generator_is_reproducible(tmp_path):
    a = pd.read_csv(create_synthetic_dataset(tmp_path / "a.csv", seed=9, farms=5, years_per_farm=2))
    b = pd.read_csv(create_synthetic_dataset(tmp_path / "b.csv", seed=9, farms=5, years_per_farm=2))
    cols=[c for c in a.columns if c != "created_at"]
    pd.testing.assert_frame_equal(a[cols], b[cols])
