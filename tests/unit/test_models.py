from app.models.registry import load_model, model_metadata, predict


def test_artifacts_load():
    assert load_model("production") is not None
    assert load_model("pest") is not None
    assert load_model("suitability") is not None


def test_prediction_shapes_and_probability_bounds():
    pest = predict("pest", {
        "annual_rainfall_mm":2200,"mean_temperature_c":27,"relative_humidity_percent":80,"average_tree_age":35,
        "yellowing":1,"crown_decline":0,"frond_cuts":0,"visible_scale_insects":0,"rhinoceros_beetle_damage":0,
        "premature_nut_fall":0,"nearby_reports":0,"symptom_severity":1,"pest_control":0,
    })
    assert 0 <= pest <= 1
    meta = model_metadata()
    assert all(v["available"] for v in meta.values())
