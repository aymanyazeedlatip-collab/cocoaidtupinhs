from __future__ import annotations

import sqlite3

from app.storage.migrations.base import Migration

LEGACY_SCHEMA_FINGERPRINT = """
farms(id,payload,created_at,updated_at);
analyses(id,input_payload,result_payload,metadata_payload,created_at);
reports(id,analysis_id,report_type,filepath,created_at);
saved_forecasts(id,farm_id,name,summary_payload,forecast_payload,created_at,updated_at);
indexes:farms.updated,analyses.created,saved_forecasts.updated
""".strip()

PHASE2_SCHEMA_FINGERPRINT = """
system_metadata(key,value,updated_at);
source_documents(id,category,title,organization,relative_path,sha256,media_type,page_count,publication_year,access_class,notes,created_at,updated_at);
coconut_varieties(id,name,code,variety_class,female_parent_code,male_parent_code,first_flowering_min_years,first_flowering_max_years,confidence,source_document_id,source_page,created_at,updated_at);
variety_parameters(id,variety_id,parameter_name,value,uncertainty,unit,verification_status,source_document_id,source_page,notes);
pest_profiles(id,common_name,scientific_name,profile_type,confidence,source_document_id,source_page,notes,created_at,updated_at);
pest_evidence_rules(id,pest_id,factor_code,direction,condition_json,likelihood_ratio,confidence,source_document_id,source_page,explanation);
pest_management_actions(id,pest_id,action_type,timing,action_text,safety_notes,source_document_id,source_page);
intercrop_candidates(id,common_name,scientific_name,light_group,min_light_fraction,max_light_fraction,confidence,source_document_id,source_page,notes,created_at,updated_at);
canopy_light_parameters(id,spacing_label,design,spacing_x_m,spacing_y_m,palms_per_hectare,palm_age_years,transmitted_light_fraction,suitable_crop_groups,confidence,source_document_id,source_page);
fertilization_scenarios(id,name,scenario_type,frequency_text,timing_text,requirements_json,confidence,source_document_id,source_page,notes,created_at,updated_at);
farmer_import_runs(id,source_document_id,source_sha256,started_at,completed_at,status,sheet_count,total_rows,accepted_rows,flagged_rows,duplicate_groups,error_count,summary_json);
farmer_registry_staging(id,import_run_id,source_sheet,source_row_number,raw_payload_json,normalized_payload_json,quality_flags_json,duplicate_group_hash,imported_at);
farmer_identities(id,import_run_id,source_sheet,source_row_number,last_name,first_name,middle_name,suffix,gender,identity_fingerprint,created_at);
farmer_registry(id,identity_id,import_run_id,source_sheet,source_row_number,region,province,municipality,barangay,absolute_area_hectares,coconut_area_hectares,tree_count,parcel_count,tree_density_per_hectare,data_quality_status,duplicate_group_hash,created_at);
farmer_quality_flags(id,farmer_registry_id,flag_code,severity,field_name,observed_value,message,created_at);
indexes:source.sha256,variety.class,pest.common,canopy.age,farmer.location,farmer.import,quality.flag
""".strip()

_CREATE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS farms (
        id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analyses (
        id TEXT PRIMARY KEY,
        input_payload TEXT NOT NULL,
        result_payload TEXT NOT NULL,
        metadata_payload TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        analysis_id TEXT,
        report_type TEXT NOT NULL DEFAULT 'pdf',
        filepath TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS saved_forecasts (
        id TEXT PRIMARY KEY,
        farm_id TEXT,
        name TEXT NOT NULL,
        summary_payload TEXT NOT NULL,
        forecast_payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_farms_updated ON farms(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_forecasts_updated ON saved_forecasts(updated_at DESC)",
)


def _legacy_schema_up(conn: sqlite3.Connection) -> None:
    for statement in _CREATE_STATEMENTS:
        conn.execute(statement)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(reports)").fetchall()}
    if "report_type" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN report_type TEXT NOT NULL DEFAULT 'pdf'")


def _legacy_schema_down(conn: sqlite3.Connection) -> None:
    for table in ("saved_forecasts", "reports", "analyses", "farms"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


def _phase2_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS system_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_documents (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL,
            page_count INTEGER,
            publication_year INTEGER,
            access_class TEXT NOT NULL DEFAULT 'internal_reference',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (page_count IS NULL OR page_count >= 1),
            CHECK (publication_year IS NULL OR publication_year BETWEEN 1900 AND 2200)
        );

        CREATE TABLE IF NOT EXISTS coconut_varieties (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            variety_class TEXT NOT NULL CHECK (variety_class IN ('tall','dwarf','hybrid')),
            female_parent_code TEXT,
            male_parent_code TEXT,
            first_flowering_min_years REAL,
            first_flowering_max_years REAL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (source_page >= 1),
            CHECK (first_flowering_min_years IS NULL OR first_flowering_min_years >= 0),
            CHECK (first_flowering_max_years IS NULL OR first_flowering_max_years >= first_flowering_min_years)
        );

        CREATE TABLE IF NOT EXISTS variety_parameters (
            id TEXT PRIMARY KEY,
            variety_id TEXT NOT NULL REFERENCES coconut_varieties(id) ON DELETE CASCADE,
            parameter_name TEXT NOT NULL,
            value REAL NOT NULL,
            uncertainty REAL,
            unit TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status IN ('verified_visual','verified_text','pending_expert_review')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            notes TEXT,
            UNIQUE (variety_id, parameter_name),
            CHECK (uncertainty IS NULL OR uncertainty >= 0),
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS pest_profiles (
            id TEXT PRIMARY KEY,
            common_name TEXT NOT NULL UNIQUE,
            scientific_name TEXT,
            profile_type TEXT NOT NULL CHECK (profile_type IN ('insect','disease')),
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS pest_evidence_rules (
            id TEXT PRIMARY KEY,
            pest_id TEXT NOT NULL REFERENCES pest_profiles(id) ON DELETE CASCADE,
            factor_code TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('increases_risk','decreases_risk','diagnostic_signal')),
            condition_json TEXT NOT NULL,
            likelihood_ratio REAL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            UNIQUE (pest_id, factor_code),
            CHECK (likelihood_ratio IS NULL OR likelihood_ratio > 0),
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS pest_management_actions (
            id TEXT PRIMARY KEY,
            pest_id TEXT NOT NULL REFERENCES pest_profiles(id) ON DELETE CASCADE,
            action_type TEXT NOT NULL,
            timing TEXT,
            action_text TEXT NOT NULL,
            safety_notes TEXT,
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS intercrop_candidates (
            id TEXT PRIMARY KEY,
            common_name TEXT NOT NULL UNIQUE,
            scientific_name TEXT,
            light_group TEXT NOT NULL CHECK (light_group IN ('A','B','C')),
            min_light_fraction REAL NOT NULL,
            max_light_fraction REAL NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (min_light_fraction BETWEEN 0 AND 1),
            CHECK (max_light_fraction BETWEEN min_light_fraction AND 1),
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS canopy_light_parameters (
            id TEXT PRIMARY KEY,
            spacing_label TEXT NOT NULL,
            design TEXT NOT NULL CHECK (design IN ('square','triangular','rectangular')),
            spacing_x_m REAL NOT NULL,
            spacing_y_m REAL NOT NULL,
            palms_per_hectare INTEGER NOT NULL,
            palm_age_years INTEGER NOT NULL CHECK (palm_age_years IN (20,40)),
            transmitted_light_fraction REAL NOT NULL,
            suitable_crop_groups TEXT NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            UNIQUE (spacing_label, palm_age_years),
            CHECK (spacing_x_m > 0 AND spacing_y_m > 0),
            CHECK (palms_per_hectare > 0),
            CHECK (transmitted_light_fraction BETWEEN 0 AND 1),
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS fertilization_scenarios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            scenario_type TEXT NOT NULL,
            frequency_text TEXT,
            timing_text TEXT,
            requirements_json TEXT NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS farmer_import_runs (
            id TEXT PRIMARY KEY,
            source_document_id TEXT REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_sha256 TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL CHECK (status IN ('running','completed','failed','dry_run')),
            sheet_count INTEGER NOT NULL DEFAULT 0,
            total_rows INTEGER NOT NULL DEFAULT 0,
            accepted_rows INTEGER NOT NULL DEFAULT 0,
            flagged_rows INTEGER NOT NULL DEFAULT 0,
            duplicate_groups INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT NOT NULL DEFAULT '{}',
            CHECK (sheet_count >= 0 AND total_rows >= 0 AND accepted_rows >= 0),
            CHECK (flagged_rows >= 0 AND duplicate_groups >= 0 AND error_count >= 0)
        );

        CREATE TABLE IF NOT EXISTS farmer_registry_staging (
            id TEXT PRIMARY KEY,
            import_run_id TEXT NOT NULL REFERENCES farmer_import_runs(id) ON DELETE CASCADE,
            source_sheet TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            raw_payload_json TEXT NOT NULL,
            normalized_payload_json TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL,
            duplicate_group_hash TEXT,
            imported_at TEXT NOT NULL,
            UNIQUE (import_run_id, source_sheet, source_row_number)
        );

        CREATE TABLE IF NOT EXISTS farmer_identities (
            id TEXT PRIMARY KEY,
            import_run_id TEXT NOT NULL REFERENCES farmer_import_runs(id) ON DELETE CASCADE,
            source_sheet TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            last_name TEXT,
            first_name TEXT,
            middle_name TEXT,
            suffix TEXT,
            gender TEXT,
            identity_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (import_run_id, source_sheet, source_row_number)
        );

        CREATE TABLE IF NOT EXISTS farmer_registry (
            id TEXT PRIMARY KEY,
            identity_id TEXT NOT NULL UNIQUE REFERENCES farmer_identities(id) ON DELETE CASCADE,
            import_run_id TEXT NOT NULL REFERENCES farmer_import_runs(id) ON DELETE CASCADE,
            source_sheet TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            region TEXT,
            province TEXT,
            municipality TEXT,
            barangay TEXT,
            absolute_area_hectares REAL,
            coconut_area_hectares REAL,
            tree_count INTEGER,
            parcel_count INTEGER,
            tree_density_per_hectare REAL,
            data_quality_status TEXT NOT NULL CHECK (data_quality_status IN ('accepted','flagged','rejected')),
            duplicate_group_hash TEXT,
            created_at TEXT NOT NULL,
            UNIQUE (import_run_id, source_sheet, source_row_number),
            CHECK (absolute_area_hectares IS NULL OR absolute_area_hectares >= 0),
            CHECK (coconut_area_hectares IS NULL OR coconut_area_hectares >= 0),
            CHECK (tree_count IS NULL OR tree_count >= 0),
            CHECK (parcel_count IS NULL OR parcel_count >= 0)
        );

        CREATE TABLE IF NOT EXISTS farmer_quality_flags (
            id TEXT PRIMARY KEY,
            farmer_registry_id TEXT NOT NULL REFERENCES farmer_registry(id) ON DELETE CASCADE,
            flag_code TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
            field_name TEXT,
            observed_value TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_source_documents_sha256 ON source_documents(sha256);
        CREATE INDEX IF NOT EXISTS idx_varieties_class ON coconut_varieties(variety_class, name);
        CREATE INDEX IF NOT EXISTS idx_variety_parameters_name ON variety_parameters(parameter_name, variety_id);
        CREATE INDEX IF NOT EXISTS idx_pest_profiles_name ON pest_profiles(common_name);
        CREATE INDEX IF NOT EXISTS idx_pest_rules_factor ON pest_evidence_rules(pest_id, factor_code);
        CREATE INDEX IF NOT EXISTS idx_canopy_light_age ON canopy_light_parameters(palm_age_years, transmitted_light_fraction);
        CREATE INDEX IF NOT EXISTS idx_farmer_import_status ON farmer_import_runs(status, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_farmer_registry_location ON farmer_registry(province, municipality, barangay);
        CREATE INDEX IF NOT EXISTS idx_farmer_registry_import ON farmer_registry(import_run_id, source_sheet);
        CREATE INDEX IF NOT EXISTS idx_farmer_duplicate_group ON farmer_registry(duplicate_group_hash);
        CREATE INDEX IF NOT EXISTS idx_farmer_quality_flag ON farmer_quality_flags(flag_code, severity);
        """
    )


def _phase2_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "farmer_quality_flags",
        "farmer_registry",
        "farmer_identities",
        "farmer_registry_staging",
        "farmer_import_runs",
        "fertilization_scenarios",
        "canopy_light_parameters",
        "intercrop_candidates",
        "pest_management_actions",
        "pest_evidence_rules",
        "pest_profiles",
        "variety_parameters",
        "coconut_varieties",
        "source_documents",
        "system_metadata",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")



PHASE3_SCHEMA_FINGERPRINT = """
weather_model_runs(id,provider,provider_model,data_kind,latitude,longitude,timezone,requested_forecast_days,requested_history_days,provider_run_at,provider_run_time_basis,retrieved_at,valid_from,valid_to,raw_payload_sha256,payload_json,units_json,quality_flags_json,provider_metadata_json,is_stale,created_at);
weather_values(id,weather_run_id,valid_at,period_kind,resolution,variable,value,unit,quality_flags_json);
weather_feature_sets(id,weather_run_id,farm_id,latitude,longitude,valid_at,feature_adapter_version,created_at);
weather_features(id,feature_set_id,name,value,unit,aggregation_window_days,derivation,quality_flags_json);
indexes:weather_runs.location,weather_runs.retrieved,weather_runs.hash,weather_values.run_time,weather_values.variable,weather_features.name
""".strip()


def _phase3_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS weather_model_runs (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            provider_model TEXT NOT NULL,
            data_kind TEXT NOT NULL CHECK (data_kind IN ('forecast','historical','observation','climate_conditioned')),
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timezone TEXT NOT NULL,
            requested_forecast_days INTEGER NOT NULL,
            requested_history_days INTEGER NOT NULL DEFAULT 0,
            provider_run_at TEXT,
            provider_run_time_basis TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT NOT NULL,
            raw_payload_sha256 TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            units_json TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            provider_metadata_json TEXT NOT NULL DEFAULT '{}',
            is_stale INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0,1)),
            created_at TEXT NOT NULL,
            CHECK (latitude BETWEEN -90 AND 90),
            CHECK (longitude BETWEEN -180 AND 180),
            CHECK (requested_forecast_days BETWEEN 0 AND 16),
            CHECK (requested_history_days BETWEEN 0 AND 92),
            CHECK (valid_to >= valid_from),
            CHECK (length(raw_payload_sha256) = 64)
        );

        CREATE TABLE IF NOT EXISTS weather_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weather_run_id TEXT NOT NULL REFERENCES weather_model_runs(id) ON DELETE CASCADE,
            valid_at TEXT NOT NULL,
            period_kind TEXT NOT NULL CHECK (period_kind IN ('historical','current','forecast')),
            resolution TEXT NOT NULL CHECK (resolution IN ('current','hourly','daily')),
            variable TEXT NOT NULL,
            value REAL,
            unit TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            UNIQUE (weather_run_id, resolution, variable, valid_at)
        );

        CREATE TABLE IF NOT EXISTS weather_feature_sets (
            id TEXT PRIMARY KEY,
            weather_run_id TEXT NOT NULL REFERENCES weather_model_runs(id) ON DELETE CASCADE,
            farm_id TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            valid_at TEXT NOT NULL,
            feature_adapter_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (weather_run_id, farm_id, feature_adapter_version)
        );

        CREATE TABLE IF NOT EXISTS weather_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_set_id TEXT NOT NULL REFERENCES weather_feature_sets(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            aggregation_window_days INTEGER,
            derivation TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            UNIQUE (feature_set_id, name),
            CHECK (aggregation_window_days IS NULL OR aggregation_window_days BETWEEN 1 AND 3660)
        );

        CREATE INDEX IF NOT EXISTS idx_weather_runs_location ON weather_model_runs(latitude, longitude, retrieved_at DESC);
        CREATE INDEX IF NOT EXISTS idx_weather_runs_retrieved ON weather_model_runs(retrieved_at DESC);
        CREATE INDEX IF NOT EXISTS idx_weather_runs_hash ON weather_model_runs(raw_payload_sha256, latitude, longitude, provider_model);
        CREATE INDEX IF NOT EXISTS idx_weather_values_run_time ON weather_values(weather_run_id, valid_at);
        CREATE INDEX IF NOT EXISTS idx_weather_values_variable ON weather_values(variable, valid_at);
        CREATE INDEX IF NOT EXISTS idx_weather_feature_sets_run ON weather_feature_sets(weather_run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_weather_features_name ON weather_features(name, feature_set_id);
        """
    )


def _phase3_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "weather_features",
        "weather_feature_sets",
        "weather_values",
        "weather_model_runs",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")



PHASE4_SCHEMA_FINGERPRINT = """
production_feature_snapshots(id,weather_feature_set_id,weather_run_id,adapter_version,feature_order_json,features_json,ordered_values_json,source_map_json,quality_flags_json,warnings_json,feature_sha256,created_at);
production_forecasts_v3(id,farm_id,cell_id,feature_snapshot_id,product,horizon_type,estimate_period,valid_from,valid_to,unit,raw_ml_prediction,variety_adjusted_prediction,posterior_json,posterior_status,probability_of_decline,model_version,feature_adapter_version,variety_id,variety_class,variety_adjustment_factor,variety_adjustment_basis,provenance_json,data_notice,warnings_json,created_at);
production_product_estimates(id,forecast_id,product,quantity,unit,estimate_kind,conversion_basis,parameter_names_json,quality_flags_json);
production_shadow_comparisons(id,forecast_id,status,legacy_prediction_tons,v3_raw_prediction_tons,v3_adjusted_prediction_tons,raw_delta_tons,adjusted_delta_tons,legacy_method,created_at);
production_actuals(id,forecast_id,farm_id,product,period_start,period_end,quantity,unit,source_type,notes,created_at);
intercrop_economic_profiles(id,source_document_id,assessment_version,site_code,crop,record_count,area_stats_json,seedling_stats_json,unit_price_stats_json,gross_income_year_stats_json,gross_income_per_hectare_stats_json,reported_cost_stats_json,frequency_labels_json,quality_flags_json,created_at,updated_at);
indexes:production.forecast_farm,production.forecast_created,production.snapshot_weather,production.product,production.actual_forecast,intercrop_economic.crop
""".strip()


def _phase4_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS production_feature_snapshots (
            id TEXT PRIMARY KEY,
            weather_feature_set_id TEXT NOT NULL REFERENCES weather_feature_sets(id) ON DELETE RESTRICT,
            weather_run_id TEXT NOT NULL REFERENCES weather_model_runs(id) ON DELETE RESTRICT,
            adapter_version TEXT NOT NULL,
            feature_order_json TEXT NOT NULL,
            features_json TEXT NOT NULL,
            ordered_values_json TEXT NOT NULL,
            source_map_json TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            warnings_json TEXT NOT NULL DEFAULT '[]',
            feature_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (length(feature_sha256) = 64)
        );

        CREATE TABLE IF NOT EXISTS production_forecasts_v3 (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            cell_id TEXT,
            feature_snapshot_id TEXT NOT NULL UNIQUE REFERENCES production_feature_snapshots(id) ON DELETE RESTRICT,
            product TEXT NOT NULL,
            horizon_type TEXT NOT NULL CHECK (horizon_type IN ('live_numerical','climate_conditioned')),
            estimate_period TEXT NOT NULL CHECK (estimate_period = 'annualized'),
            valid_from TEXT NOT NULL,
            valid_to TEXT NOT NULL,
            unit TEXT NOT NULL,
            raw_ml_prediction REAL,
            variety_adjusted_prediction REAL,
            posterior_json TEXT,
            posterior_status TEXT NOT NULL CHECK (posterior_status IN ('not_run','available')),
            probability_of_decline REAL,
            model_version TEXT NOT NULL,
            feature_adapter_version TEXT NOT NULL,
            variety_id TEXT REFERENCES coconut_varieties(id) ON DELETE SET NULL,
            variety_class TEXT NOT NULL CHECK (variety_class IN ('Tall','Dwarf','Hybrid','Unknown')),
            variety_adjustment_factor REAL NOT NULL,
            variety_adjustment_basis TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            data_notice TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            CHECK (valid_to >= valid_from),
            CHECK (raw_ml_prediction IS NULL OR raw_ml_prediction >= 0),
            CHECK (variety_adjusted_prediction IS NULL OR variety_adjusted_prediction >= 0),
            CHECK (probability_of_decline IS NULL OR probability_of_decline BETWEEN 0 AND 1),
            CHECK (variety_adjustment_factor BETWEEN 0.5 AND 1.5),
            CHECK ((posterior_status = 'not_run' AND posterior_json IS NULL) OR (posterior_status = 'available' AND posterior_json IS NOT NULL))
        );

        CREATE TABLE IF NOT EXISTS production_product_estimates (
            id TEXT PRIMARY KEY,
            forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE CASCADE,
            product TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            estimate_kind TEXT NOT NULL CHECK (estimate_kind IN ('direct_model_output','variety_conversion','official_share_split')),
            conversion_basis TEXT NOT NULL,
            parameter_names_json TEXT NOT NULL DEFAULT '[]',
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            UNIQUE (forecast_id, product),
            CHECK (quantity >= 0)
        );

        CREATE TABLE IF NOT EXISTS production_shadow_comparisons (
            id TEXT PRIMARY KEY,
            forecast_id TEXT NOT NULL UNIQUE REFERENCES production_forecasts_v3(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (status IN ('available','not_available')),
            legacy_prediction_tons REAL,
            v3_raw_prediction_tons REAL NOT NULL,
            v3_adjusted_prediction_tons REAL NOT NULL,
            raw_delta_tons REAL,
            adjusted_delta_tons REAL,
            legacy_method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (legacy_prediction_tons IS NULL OR legacy_prediction_tons >= 0),
            CHECK (v3_raw_prediction_tons >= 0),
            CHECK (v3_adjusted_prediction_tons >= 0)
        );

        CREATE TABLE IF NOT EXISTS production_actuals (
            id TEXT PRIMARY KEY,
            forecast_id TEXT REFERENCES production_forecasts_v3(id) ON DELETE SET NULL,
            farm_id TEXT NOT NULL,
            product TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK (source_type IN ('measured','farmer_reported','government_record')),
            notes TEXT,
            created_at TEXT NOT NULL,
            CHECK (period_end >= period_start),
            CHECK (quantity >= 0)
        );

        CREATE TABLE IF NOT EXISTS intercrop_economic_profiles (
            id TEXT PRIMARY KEY,
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            assessment_version TEXT NOT NULL,
            site_code TEXT NOT NULL,
            crop TEXT NOT NULL CHECK (crop IN ('cacao','coffee')),
            record_count INTEGER NOT NULL,
            area_stats_json TEXT NOT NULL,
            seedling_stats_json TEXT NOT NULL,
            unit_price_stats_json TEXT NOT NULL,
            gross_income_year_stats_json TEXT NOT NULL,
            gross_income_per_hectare_stats_json TEXT NOT NULL,
            reported_cost_stats_json TEXT NOT NULL,
            frequency_labels_json TEXT NOT NULL,
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (assessment_version, site_code, crop),
            CHECK (record_count >= 1)
        );

        CREATE INDEX IF NOT EXISTS idx_production_forecast_farm ON production_forecasts_v3(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_production_forecast_created ON production_forecasts_v3(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_production_snapshot_weather ON production_feature_snapshots(weather_run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_production_product ON production_product_estimates(product, forecast_id);
        CREATE INDEX IF NOT EXISTS idx_production_actual_forecast ON production_actuals(forecast_id, period_end DESC);
        CREATE INDEX IF NOT EXISTS idx_intercrop_economic_crop ON intercrop_economic_profiles(crop, site_code);
        """
    )


def _phase4_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "intercrop_economic_profiles",
        "production_actuals",
        "production_shadow_comparisons",
        "production_product_estimates",
        "production_forecasts_v3",
        "production_feature_snapshots",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE5_SCHEMA_FINGERPRINT = """
bayesian_evidence_observations(id,farm_id,cell_id,production_forecast_id,evidence_type,evidence_status,observed_at,value,unit,notes,source_label,created_at);
bayesian_runs(id,posterior_id,production_forecast_id,farm_id,cell_id,prior_posterior_id,baseline_state_date,valid_at,horizon_months,particle_count,random_seed,intervention,evidence_ids_json,diagnostics_json,data_notice,warnings_json,created_at);
bayesian_posteriors(id,run_id,state_json,state_intervals_json,production_distribution_json,base_production_tonnes,probability_of_decline,probability_of_recovery,probability_of_tree_mortality,probability_of_pest_outbreak,uncertainty_sources_json,provenance_json,created_at);
bayesian_parameter_posteriors(posterior_id,name,distribution,parameters_json,posterior_mean,credible_interval_json);
bayesian_evidence_assimilation(posterior_id,observation_id,evidence_type,evidence_status,used_for_update,reliability_weight,ess_before,ess_after,resampled,explanation);
indexes:bayesian.evidence_farm,bayesian.evidence_forecast,bayesian.run_farm,bayesian.run_forecast,bayesian.run_prior,bayesian.parameter_name
""".strip()


def _phase5_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bayesian_evidence_observations (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            cell_id TEXT,
            production_forecast_id TEXT REFERENCES production_forecasts_v3(id) ON DELETE SET NULL,
            evidence_type TEXT NOT NULL CHECK (evidence_type IN (
                'harvest','pest_prevalence','tree_mortality','storm_damage',
                'rehabilitation_completion','actual_rainfall'
            )),
            evidence_status TEXT NOT NULL CHECK (evidence_status IN (
                'predicted','suspected','farmer_reported','field_confirmed','expert_confirmed'
            )),
            observed_at TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            notes TEXT,
            source_label TEXT,
            created_at TEXT NOT NULL,
            CHECK (value >= 0)
        );

        CREATE TABLE IF NOT EXISTS bayesian_runs (
            id TEXT PRIMARY KEY,
            posterior_id TEXT NOT NULL UNIQUE,
            production_forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE RESTRICT,
            farm_id TEXT NOT NULL,
            cell_id TEXT,
            prior_posterior_id TEXT REFERENCES bayesian_posteriors(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
            baseline_state_date TEXT NOT NULL,
            valid_at TEXT NOT NULL,
            horizon_months INTEGER NOT NULL,
            particle_count INTEGER NOT NULL,
            random_seed INTEGER NOT NULL,
            intervention TEXT NOT NULL CHECK (intervention IN (
                'none','monitoring','pest_control','soil_rehabilitation','replanting','combined'
            )),
            evidence_ids_json TEXT NOT NULL DEFAULT '[]',
            diagnostics_json TEXT NOT NULL,
            data_notice TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            CHECK (horizon_months BETWEEN 1 AND 60),
            CHECK (particle_count BETWEEN 100 AND 5000),
            CHECK (random_seed BETWEEN 0 AND 2147483647)
        );

        CREATE TABLE IF NOT EXISTS bayesian_posteriors (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL UNIQUE REFERENCES bayesian_runs(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
            state_json TEXT NOT NULL,
            state_intervals_json TEXT NOT NULL DEFAULT '[]',
            production_distribution_json TEXT NOT NULL,
            base_production_tonnes REAL,
            probability_of_decline REAL NOT NULL,
            probability_of_recovery REAL NOT NULL,
            probability_of_tree_mortality REAL NOT NULL,
            probability_of_pest_outbreak REAL NOT NULL,
            uncertainty_sources_json TEXT NOT NULL DEFAULT '[]',
            provenance_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (base_production_tonnes IS NULL OR base_production_tonnes >= 0),
            CHECK (probability_of_decline BETWEEN 0 AND 1),
            CHECK (probability_of_recovery BETWEEN 0 AND 1),
            CHECK (probability_of_tree_mortality BETWEEN 0 AND 1),
            CHECK (probability_of_pest_outbreak BETWEEN 0 AND 1)
        );

        CREATE TABLE IF NOT EXISTS bayesian_parameter_posteriors (
            posterior_id TEXT NOT NULL REFERENCES bayesian_posteriors(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            distribution TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            posterior_mean REAL,
            credible_interval_json TEXT,
            PRIMARY KEY (posterior_id, name)
        );

        CREATE TABLE IF NOT EXISTS bayesian_evidence_assimilation (
            posterior_id TEXT NOT NULL REFERENCES bayesian_posteriors(id) ON DELETE CASCADE,
            observation_id TEXT NOT NULL REFERENCES bayesian_evidence_observations(id) ON DELETE RESTRICT,
            evidence_type TEXT NOT NULL,
            evidence_status TEXT NOT NULL,
            used_for_update INTEGER NOT NULL CHECK (used_for_update IN (0,1)),
            reliability_weight REAL NOT NULL,
            ess_before REAL,
            ess_after REAL,
            resampled INTEGER NOT NULL CHECK (resampled IN (0,1)),
            explanation TEXT NOT NULL,
            PRIMARY KEY (posterior_id, observation_id),
            CHECK (reliability_weight BETWEEN 0 AND 1),
            CHECK (ess_before IS NULL OR ess_before >= 0),
            CHECK (ess_after IS NULL OR ess_after >= 0)
        );

        CREATE INDEX IF NOT EXISTS idx_bayesian_evidence_farm
            ON bayesian_evidence_observations(farm_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bayesian_evidence_forecast
            ON bayesian_evidence_observations(production_forecast_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bayesian_run_farm
            ON bayesian_runs(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bayesian_run_forecast
            ON bayesian_runs(production_forecast_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bayesian_run_prior
            ON bayesian_runs(prior_posterior_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bayesian_parameter_name
            ON bayesian_parameter_posteriors(name, posterior_id);
        """
    )


def _phase5_schema_down(conn: sqlite3.Connection) -> None:
    # Runs and posteriors deliberately form a provenance-preserving relationship.
    # Break sequential-posterior references before destructive rollback so a
    # populated disposable database can still be downgraded deterministically.
    conn.execute("UPDATE bayesian_runs SET prior_posterior_id = NULL")
    conn.execute(
        "UPDATE production_forecasts_v3 "
        "SET posterior_json = NULL, posterior_status = 'not_run', probability_of_decline = NULL "
        "WHERE posterior_status = 'available'"
    )
    conn.execute("DELETE FROM bayesian_evidence_assimilation")
    conn.execute("DELETE FROM bayesian_parameter_posteriors")
    conn.execute("DELETE FROM bayesian_runs")
    for table in (
        "bayesian_evidence_assimilation",
        "bayesian_parameter_posteriors",
        "bayesian_posteriors",
        "bayesian_runs",
        "bayesian_evidence_observations",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE6_SCHEMA_FINGERPRINT = """
pest_observations_v3(id,farm_id,cell_id,production_forecast_id,pest_profile_id,factor_code,evidence_status,observed_at,value_json,unit,prevalence_fraction,latitude,longitude,source_label,notes,bayesian_observation_id,created_at);
pest_assessment_runs(id,farm_id,cell_id,production_forecast_id,posterior_id,weather_feature_set_id,weather_run_id,assessed_at,requested_pest_ids_json,farm_context_json,observation_ids_json,nearby_cases_json,parameter_version,data_notice,taxonomy_notice,warnings_json,created_at);
pest_assessments_v3(id,run_id,pest_profile_id,outbreak_probability,risk_class,severity_if_outbreak,exposed_palms,conditional_loss,expected_loss,loss_unit,spatial_pressure,recommended_inspection_at,quarantine_warning,profile_snapshot_json,provenance_json,created_at);
pest_assessment_contributions(assessment_id,sequence,factor_code,source_kind,direction,matched,likelihood_ratio,log_odds_delta,confidence,evidence_status,explanation,source_document_id,source_page);
pest_assessment_actions(assessment_id,sequence,action_type,timing,action_text,safety_notes,source_document_id,source_page);
indexes:pest.observation_farm,pest.observation_profile,pest.run_farm,pest.run_forecast,pest.assessment_profile,pest.assessment_probability
""".strip()


def _phase6_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pest_observations_v3 (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            cell_id TEXT,
            production_forecast_id TEXT REFERENCES production_forecasts_v3(id) ON DELETE SET NULL,
            pest_profile_id TEXT NOT NULL REFERENCES pest_profiles(id) ON DELETE RESTRICT,
            factor_code TEXT NOT NULL,
            evidence_status TEXT NOT NULL CHECK (evidence_status IN (
                'predicted','suspected','farmer_reported','field_confirmed','expert_confirmed'
            )),
            observed_at TEXT NOT NULL,
            value_json TEXT NOT NULL,
            unit TEXT,
            prevalence_fraction REAL,
            latitude REAL,
            longitude REAL,
            source_label TEXT,
            notes TEXT,
            bayesian_observation_id TEXT REFERENCES bayesian_evidence_observations(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            CHECK (prevalence_fraction IS NULL OR prevalence_fraction BETWEEN 0 AND 1),
            CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
            CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
            CHECK ((latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL))
        );

        CREATE TABLE IF NOT EXISTS pest_assessment_runs (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            cell_id TEXT,
            production_forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE RESTRICT,
            posterior_id TEXT REFERENCES bayesian_posteriors(id) ON DELETE RESTRICT,
            weather_feature_set_id TEXT NOT NULL REFERENCES weather_feature_sets(id) ON DELETE RESTRICT,
            weather_run_id TEXT NOT NULL REFERENCES weather_model_runs(id) ON DELETE RESTRICT,
            assessed_at TEXT NOT NULL,
            requested_pest_ids_json TEXT NOT NULL,
            farm_context_json TEXT NOT NULL,
            observation_ids_json TEXT NOT NULL DEFAULT '[]',
            nearby_cases_json TEXT NOT NULL DEFAULT '[]',
            parameter_version TEXT NOT NULL,
            data_notice TEXT NOT NULL,
            taxonomy_notice TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pest_assessments_v3 (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES pest_assessment_runs(id) ON DELETE CASCADE,
            pest_profile_id TEXT NOT NULL REFERENCES pest_profiles(id) ON DELETE RESTRICT,
            outbreak_probability REAL NOT NULL,
            risk_class TEXT NOT NULL CHECK (risk_class IN ('low','moderate','high','critical')),
            severity_if_outbreak REAL NOT NULL,
            exposed_palms INTEGER NOT NULL,
            conditional_loss REAL NOT NULL,
            expected_loss REAL NOT NULL,
            loss_unit TEXT NOT NULL,
            spatial_pressure REAL NOT NULL,
            recommended_inspection_at TEXT NOT NULL,
            quarantine_warning TEXT,
            profile_snapshot_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (run_id, pest_profile_id),
            CHECK (outbreak_probability BETWEEN 0 AND 1),
            CHECK (severity_if_outbreak BETWEEN 0 AND 1),
            CHECK (exposed_palms >= 0),
            CHECK (conditional_loss >= 0),
            CHECK (expected_loss >= 0),
            CHECK (expected_loss <= conditional_loss + 0.000000001),
            CHECK (spatial_pressure BETWEEN 0 AND 1)
        );

        CREATE TABLE IF NOT EXISTS pest_assessment_contributions (
            assessment_id TEXT NOT NULL REFERENCES pest_assessments_v3(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            factor_code TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('increases_risk','decreases_risk','diagnostic_signal')),
            matched INTEGER NOT NULL CHECK (matched IN (0,1)),
            likelihood_ratio REAL NOT NULL,
            log_odds_delta REAL NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            evidence_status TEXT,
            explanation TEXT NOT NULL,
            source_document_id TEXT REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER,
            PRIMARY KEY (assessment_id, sequence),
            CHECK (likelihood_ratio > 0),
            CHECK (source_page IS NULL OR source_page >= 1)
        );

        CREATE TABLE IF NOT EXISTS pest_assessment_actions (
            assessment_id TEXT NOT NULL REFERENCES pest_assessments_v3(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            timing TEXT,
            action_text TEXT NOT NULL,
            safety_notes TEXT,
            source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
            source_page INTEGER NOT NULL,
            PRIMARY KEY (assessment_id, sequence),
            CHECK (source_page >= 1)
        );

        CREATE INDEX IF NOT EXISTS idx_pest_observation_farm
            ON pest_observations_v3(farm_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pest_observation_profile
            ON pest_observations_v3(pest_profile_id, observed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pest_run_farm
            ON pest_assessment_runs(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pest_run_forecast
            ON pest_assessment_runs(production_forecast_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pest_assessment_profile
            ON pest_assessments_v3(pest_profile_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pest_assessment_probability
            ON pest_assessments_v3(outbreak_probability DESC, created_at DESC);
        """
    )


def _phase6_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "pest_assessment_actions",
        "pest_assessment_contributions",
        "pest_assessments_v3",
        "pest_assessment_runs",
        "pest_observations_v3",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE7_SCHEMA_FINGERPRINT = """
intercrop_requirement_profiles(candidate_id,profile_version,min_temperature_c,max_temperature_c,min_rainfall_mm_year,max_rainfall_mm_year,min_soil_ph,max_soil_ph,min_soil_moisture_index,max_soil_moisture_index,min_drainage_index,water_demand,root_competition,space_demand,nutrient_demand,management_demand,pest_conflict_ids_json,beneficial_pest_ids_json,economic_profile_crop,planting_months_json,harvest_months_json,confidence,basis,notes,created_at,updated_at);
intercrop_assessment_runs(id,farm_id,production_forecast_id,posterior_id,pest_assessment_run_id,weather_feature_set_id,weather_run_id,assessed_at,candidate_ids_json,cell_contexts_json,parameter_version,requirement_profile_version,data_notice,warnings_json,summary_json,created_at);
intercrop_cell_assessments(id,run_id,cell_id,cell_label,candidate_id,suitability_score,suitability_class,hard_constraint_passed,canopy_light_json,coconut_competition_risk,pest_conflict_risk,limiting_factors_json,planting_window_start,planting_window_end,recommended_layout,economic_potential_json,confidence,data_quality_notes_json,candidate_snapshot_json,provenance_json,created_at);
intercrop_component_scores(assessment_id,sequence,factor,score,weight,hard_constraint_passed,explanation);
indexes:intercrop.run_farm,intercrop.run_forecast,intercrop.assessment_cell,intercrop.assessment_candidate,intercrop.assessment_score
""".strip()


def _phase7_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS intercrop_requirement_profiles (
            candidate_id TEXT PRIMARY KEY REFERENCES intercrop_candidates(id) ON DELETE CASCADE,
            profile_version TEXT NOT NULL,
            min_temperature_c REAL NOT NULL,
            max_temperature_c REAL NOT NULL,
            min_rainfall_mm_year REAL NOT NULL,
            max_rainfall_mm_year REAL NOT NULL,
            min_soil_ph REAL NOT NULL,
            max_soil_ph REAL NOT NULL,
            min_soil_moisture_index REAL NOT NULL,
            max_soil_moisture_index REAL NOT NULL,
            min_drainage_index REAL NOT NULL,
            water_demand REAL NOT NULL,
            root_competition REAL NOT NULL,
            space_demand REAL NOT NULL,
            nutrient_demand REAL NOT NULL,
            management_demand REAL NOT NULL,
            pest_conflict_ids_json TEXT NOT NULL DEFAULT '[]',
            beneficial_pest_ids_json TEXT NOT NULL DEFAULT '[]',
            economic_profile_crop TEXT,
            planting_months_json TEXT NOT NULL DEFAULT '[]',
            harvest_months_json TEXT NOT NULL DEFAULT '[]',
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            basis TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (min_temperature_c <= max_temperature_c),
            CHECK (min_rainfall_mm_year <= max_rainfall_mm_year),
            CHECK (min_soil_ph <= max_soil_ph),
            CHECK (min_soil_moisture_index BETWEEN 0 AND 1),
            CHECK (max_soil_moisture_index BETWEEN min_soil_moisture_index AND 1),
            CHECK (min_drainage_index BETWEEN 0 AND 1),
            CHECK (water_demand BETWEEN 0 AND 1),
            CHECK (root_competition BETWEEN 0 AND 1),
            CHECK (space_demand BETWEEN 0 AND 1),
            CHECK (nutrient_demand BETWEEN 0 AND 1),
            CHECK (management_demand BETWEEN 0 AND 1)
        );

        CREATE TABLE IF NOT EXISTS intercrop_assessment_runs (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            production_forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE RESTRICT,
            posterior_id TEXT REFERENCES bayesian_posteriors(id) ON DELETE RESTRICT,
            pest_assessment_run_id TEXT REFERENCES pest_assessment_runs(id) ON DELETE RESTRICT,
            weather_feature_set_id TEXT NOT NULL REFERENCES weather_feature_sets(id) ON DELETE RESTRICT,
            weather_run_id TEXT NOT NULL REFERENCES weather_model_runs(id) ON DELETE RESTRICT,
            assessed_at TEXT NOT NULL,
            candidate_ids_json TEXT NOT NULL,
            cell_contexts_json TEXT NOT NULL,
            parameter_version TEXT NOT NULL,
            requirement_profile_version TEXT NOT NULL,
            data_notice TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            summary_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS intercrop_cell_assessments (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES intercrop_assessment_runs(id) ON DELETE CASCADE,
            cell_id TEXT NOT NULL,
            cell_label TEXT NOT NULL,
            candidate_id TEXT NOT NULL REFERENCES intercrop_candidates(id) ON DELETE RESTRICT,
            suitability_score REAL NOT NULL,
            suitability_class TEXT NOT NULL CHECK (suitability_class IN ('unsuitable','low','moderate','high','very_high')),
            hard_constraint_passed INTEGER NOT NULL CHECK (hard_constraint_passed IN (0,1)),
            canopy_light_json TEXT NOT NULL,
            coconut_competition_risk REAL NOT NULL,
            pest_conflict_risk REAL NOT NULL,
            limiting_factors_json TEXT NOT NULL DEFAULT '[]',
            planting_window_start TEXT,
            planting_window_end TEXT,
            recommended_layout TEXT NOT NULL,
            economic_potential_json TEXT NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            data_quality_notes_json TEXT NOT NULL DEFAULT '[]',
            candidate_snapshot_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (run_id, cell_id, candidate_id),
            CHECK (suitability_score BETWEEN 0 AND 100),
            CHECK (coconut_competition_risk BETWEEN 0 AND 1),
            CHECK (pest_conflict_risk BETWEEN 0 AND 1),
            CHECK (hard_constraint_passed = 1 OR suitability_score <= 40.000000001)
        );

        CREATE TABLE IF NOT EXISTS intercrop_component_scores (
            assessment_id TEXT NOT NULL REFERENCES intercrop_cell_assessments(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            factor TEXT NOT NULL,
            score REAL NOT NULL,
            weight REAL NOT NULL,
            hard_constraint_passed INTEGER NOT NULL CHECK (hard_constraint_passed IN (0,1)),
            explanation TEXT NOT NULL,
            PRIMARY KEY (assessment_id, sequence),
            CHECK (score BETWEEN 0 AND 1),
            CHECK (weight > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_intercrop_run_farm
            ON intercrop_assessment_runs(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intercrop_run_forecast
            ON intercrop_assessment_runs(production_forecast_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_intercrop_assessment_cell
            ON intercrop_cell_assessments(cell_id, suitability_score DESC);
        CREATE INDEX IF NOT EXISTS idx_intercrop_assessment_candidate
            ON intercrop_cell_assessments(candidate_id, suitability_score DESC);
        CREATE INDEX IF NOT EXISTS idx_intercrop_assessment_score
            ON intercrop_cell_assessments(suitability_score DESC, created_at DESC);
        """
    )


def _phase7_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "intercrop_component_scores",
        "intercrop_cell_assessments",
        "intercrop_assessment_runs",
        "intercrop_requirement_profiles",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE8_SCHEMA_FINGERPRINT = """
rehabilitation_plan_runs(id,farm_id,production_forecast_id,posterior_id,pest_assessment_run_id,intercropping_run_id,planned_at,cell_contexts_json,total_budget_php,available_labor_person_days,planning_horizon_months,annual_discount_rate,risk_aversion,farm_data_version,parameter_version,cost_catalog_version,linked_weather_run_id,selected_scenario,total_expected_cost_php,unallocated_budget_php,summary_json,warnings_json,data_notice,provenance_json,created_at);
rehabilitation_actions_v3(id,plan_id,cell_id,action_type,timing,priority,problem_detected,likely_cause,triggers_json,evidence_ids_json,instructions_json,required_materials_json,scheduled_date,follow_up_dates_json,materials_php,labor_php,other_php,total_php,labor_person_days,cost_basis,expected_recovery_days,expected_production_regained_lower,expected_production_regained_median,expected_production_regained_upper,production_regained_unit,confidence,requires_field_confirmation,parameter_basis,created_at);
rehabilitation_scenario_results(id,plan_id,scenario_type,status,action_ids_json,total_cost_php,labor_person_days,coconut_production_lower_tonnes,coconut_production_median_tonnes,coconut_production_upper_tonnes,intercrop_gross_revenue_lower_php,intercrop_gross_revenue_median_php,intercrop_gross_revenue_upper_php,severe_loss_probability,expected_utility,utility_components_json,feasibility_reasons_json,assumptions_json,created_at);
indexes:rehabilitation.plan_farm,rehabilitation.plan_forecast,rehabilitation.action_cell,rehabilitation.scenario_plan
""".strip()


def _phase8_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rehabilitation_plan_runs (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            production_forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE RESTRICT,
            posterior_id TEXT REFERENCES bayesian_posteriors(id) ON DELETE RESTRICT,
            pest_assessment_run_id TEXT REFERENCES pest_assessment_runs(id) ON DELETE RESTRICT,
            intercropping_run_id TEXT REFERENCES intercrop_assessment_runs(id) ON DELETE RESTRICT,
            planned_at TEXT NOT NULL,
            cell_contexts_json TEXT NOT NULL,
            total_budget_php REAL,
            available_labor_person_days REAL,
            planning_horizon_months INTEGER NOT NULL,
            annual_discount_rate REAL NOT NULL,
            risk_aversion REAL NOT NULL,
            farm_data_version TEXT NOT NULL,
            parameter_version TEXT NOT NULL,
            cost_catalog_version TEXT NOT NULL,
            linked_weather_run_id TEXT REFERENCES weather_model_runs(id) ON DELETE RESTRICT,
            selected_scenario TEXT NOT NULL CHECK (selected_scenario IN (
                'no_action','pest_management','fertilization','replanting','intercropping','combined_rehabilitation'
            )),
            total_expected_cost_php REAL NOT NULL,
            unallocated_budget_php REAL,
            summary_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            data_notice TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (total_budget_php IS NULL OR total_budget_php >= 0),
            CHECK (available_labor_person_days IS NULL OR available_labor_person_days >= 0),
            CHECK (planning_horizon_months BETWEEN 1 AND 120),
            CHECK (annual_discount_rate BETWEEN 0 AND 1),
            CHECK (risk_aversion BETWEEN 0 AND 2),
            CHECK (total_expected_cost_php >= 0),
            CHECK (unallocated_budget_php IS NULL OR unallocated_budget_php >= 0),
            CHECK (total_budget_php IS NULL OR total_expected_cost_php <= total_budget_php + 0.01)
        );

        CREATE TABLE IF NOT EXISTS rehabilitation_actions_v3 (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL REFERENCES rehabilitation_plan_runs(id) ON DELETE CASCADE,
            cell_id TEXT,
            action_type TEXT NOT NULL CHECK (action_type IN (
                'inspect','monitor','sanitation','remove_breeding_material','drainage_improvement',
                'organic_matter_application','fertilizer_correction','pest_or_disease_treatment',
                'pruning_or_crown_management','partial_replanting','complete_replanting',
                'variety_replacement','intercropping_adjustment'
            )),
            timing TEXT NOT NULL CHECK (timing IN ('pre_event','post_event_inspection','post_confirmation','routine')),
            priority TEXT NOT NULL CHECK (priority IN ('routine','low','moderate','high','critical')),
            problem_detected TEXT NOT NULL,
            likely_cause TEXT NOT NULL,
            triggers_json TEXT NOT NULL DEFAULT '[]',
            evidence_ids_json TEXT NOT NULL DEFAULT '[]',
            instructions_json TEXT NOT NULL,
            required_materials_json TEXT NOT NULL DEFAULT '[]',
            scheduled_date TEXT,
            follow_up_dates_json TEXT NOT NULL DEFAULT '[]',
            materials_php REAL NOT NULL,
            labor_php REAL NOT NULL,
            other_php REAL NOT NULL,
            total_php REAL NOT NULL,
            labor_person_days REAL,
            cost_basis TEXT,
            expected_recovery_days INTEGER,
            expected_production_regained_lower REAL,
            expected_production_regained_median REAL,
            expected_production_regained_upper REAL,
            production_regained_unit TEXT,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            requires_field_confirmation INTEGER NOT NULL CHECK (requires_field_confirmation IN (0,1)),
            parameter_basis TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (materials_php >= 0 AND labor_php >= 0 AND other_php >= 0 AND total_php >= 0),
            CHECK (ABS(total_php - (materials_php + labor_php + other_php)) <= MAX(0.01,total_php*0.001)),
            CHECK (labor_person_days IS NULL OR labor_person_days >= 0),
            CHECK (expected_recovery_days IS NULL OR expected_recovery_days >= 0),
            CHECK (expected_production_regained_lower IS NULL OR expected_production_regained_lower >= 0),
            CHECK (expected_production_regained_median IS NULL OR expected_production_regained_median >= expected_production_regained_lower),
            CHECK (expected_production_regained_upper IS NULL OR expected_production_regained_upper >= expected_production_regained_median)
        );

        CREATE TABLE IF NOT EXISTS rehabilitation_scenario_results (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL REFERENCES rehabilitation_plan_runs(id) ON DELETE CASCADE,
            scenario_type TEXT NOT NULL CHECK (scenario_type IN (
                'no_action','pest_management','fertilization','replanting','intercropping','combined_rehabilitation'
            )),
            status TEXT NOT NULL CHECK (status IN ('feasible','infeasible_budget','infeasible_labor','not_applicable')),
            action_ids_json TEXT NOT NULL DEFAULT '[]',
            total_cost_php REAL NOT NULL,
            labor_person_days REAL NOT NULL,
            coconut_production_lower_tonnes REAL NOT NULL,
            coconut_production_median_tonnes REAL NOT NULL,
            coconut_production_upper_tonnes REAL NOT NULL,
            intercrop_gross_revenue_lower_php REAL NOT NULL DEFAULT 0,
            intercrop_gross_revenue_median_php REAL NOT NULL DEFAULT 0,
            intercrop_gross_revenue_upper_php REAL NOT NULL DEFAULT 0,
            severe_loss_probability REAL NOT NULL,
            expected_utility REAL NOT NULL,
            utility_components_json TEXT NOT NULL,
            feasibility_reasons_json TEXT NOT NULL DEFAULT '[]',
            assumptions_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            UNIQUE (plan_id, scenario_type),
            CHECK (total_cost_php >= 0 AND labor_person_days >= 0),
            CHECK (coconut_production_lower_tonnes >= 0),
            CHECK (coconut_production_lower_tonnes <= coconut_production_median_tonnes),
            CHECK (coconut_production_median_tonnes <= coconut_production_upper_tonnes),
            CHECK (intercrop_gross_revenue_lower_php >= 0),
            CHECK (intercrop_gross_revenue_lower_php <= intercrop_gross_revenue_median_php),
            CHECK (intercrop_gross_revenue_median_php <= intercrop_gross_revenue_upper_php),
            CHECK (severe_loss_probability BETWEEN 0 AND 1)
        );

        CREATE INDEX IF NOT EXISTS idx_rehabilitation_plan_farm
            ON rehabilitation_plan_runs(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_rehabilitation_plan_forecast
            ON rehabilitation_plan_runs(production_forecast_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_rehabilitation_action_cell
            ON rehabilitation_actions_v3(cell_id, priority, scheduled_date);
        CREATE INDEX IF NOT EXISTS idx_rehabilitation_scenario_plan
            ON rehabilitation_scenario_results(plan_id, expected_utility DESC);
        """
    )


def _phase8_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        "rehabilitation_scenario_results",
        "rehabilitation_actions_v3",
        "rehabilitation_plan_runs",
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE9_SCHEMA_FINGERPRINT = """
decision_support_runs(id,farm_id,generated_at,status,requested_components_json,production_forecast_id,posterior_id,pest_assessment_run_id,intercropping_run_id,rehabilitation_plan_id,overview_json,summary_json,parameter_version,dependency_graph_version,provenance_json,warnings_json,data_notice,created_at);
decision_support_components(run_id,component,engine_id,status,record_id,summary_json,warnings_json,errors_json);
decision_support_recommendations(id,run_id,sequence,category,priority,title,action,rationale,confidence,source_components_json,evidence_json,requires_field_confirmation,limitations_json,created_at);
decision_support_trace_edges(run_id,sequence,upstream_component,downstream_component,relationship,upstream_record_id,downstream_record_id);
indexes:decision_support.run_farm,decision_support.run_status,decision_support.recommendation_priority
""".strip()


def _phase9_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS decision_support_runs (
            id TEXT PRIMARY KEY,
            farm_id TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('completed','partially_completed','failed')),
            requested_components_json TEXT NOT NULL,
            production_forecast_id TEXT NOT NULL REFERENCES production_forecasts_v3(id) ON DELETE RESTRICT,
            posterior_id TEXT REFERENCES bayesian_posteriors(id) ON DELETE RESTRICT,
            pest_assessment_run_id TEXT REFERENCES pest_assessment_runs(id) ON DELETE RESTRICT,
            intercropping_run_id TEXT REFERENCES intercrop_assessment_runs(id) ON DELETE RESTRICT,
            rehabilitation_plan_id TEXT REFERENCES rehabilitation_plan_runs(id) ON DELETE RESTRICT,
            overview_json TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            parameter_version TEXT NOT NULL,
            dependency_graph_version TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            data_notice TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decision_support_components (
            run_id TEXT NOT NULL REFERENCES decision_support_runs(id) ON DELETE CASCADE,
            component TEXT NOT NULL CHECK (component IN ('production','bayesian','pest','intercropping','rehabilitation')),
            engine_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('succeeded','failed','skipped','degraded')),
            record_id TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}',
            warnings_json TEXT NOT NULL DEFAULT '[]',
            errors_json TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (run_id, component)
        );

        CREATE TABLE IF NOT EXISTS decision_support_recommendations (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES decision_support_runs(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('routine','low','moderate','high','critical')),
            title TEXT NOT NULL,
            action TEXT NOT NULL,
            rationale TEXT NOT NULL,
            confidence TEXT NOT NULL CHECK (confidence IN ('low','moderate','high')),
            source_components_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            requires_field_confirmation INTEGER NOT NULL CHECK (requires_field_confirmation IN (0,1)),
            limitations_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            UNIQUE (run_id, sequence)
        );

        CREATE TABLE IF NOT EXISTS decision_support_trace_edges (
            run_id TEXT NOT NULL REFERENCES decision_support_runs(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            upstream_component TEXT NOT NULL CHECK (upstream_component IN ('production','bayesian','pest','intercropping','rehabilitation')),
            downstream_component TEXT NOT NULL CHECK (downstream_component IN ('production','bayesian','pest','intercropping','rehabilitation')),
            relationship TEXT NOT NULL,
            upstream_record_id TEXT,
            downstream_record_id TEXT,
            PRIMARY KEY (run_id, sequence)
        );

        CREATE INDEX IF NOT EXISTS idx_decision_support_run_farm
            ON decision_support_runs(farm_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decision_support_run_status
            ON decision_support_runs(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decision_support_recommendation_priority
            ON decision_support_recommendations(priority, run_id, sequence);
        """
    )


def _phase9_schema_down(conn: sqlite3.Connection) -> None:
    for table in (
        'decision_support_trace_edges',
        'decision_support_recommendations',
        'decision_support_components',
        'decision_support_runs',
    ):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


PHASE10_SCHEMA_FINGERPRINT = """
coco_pilot_runs(id,analysis_run_id,mode,provider,provider_model,status,conclusion,bullets_json,action_line,full_text,citations_json,source_manifest_json,redaction_summary_json,warnings_json,limitations_json,created_at);
formal_report_runs(id,analysis_run_id,narrative_run_id,report_format,filename,filepath,file_sha256,content_fingerprint,generator_version,source_manifest_json,warnings_json,data_notice,created_at);
indexes:coco_pilot.analysis,coco_pilot.mode,formal_report.analysis,formal_report.fingerprint
""".strip()


def _phase10_schema_up(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS coco_pilot_runs (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL REFERENCES decision_support_runs(id) ON DELETE CASCADE,
            mode TEXT NOT NULL CHECK (mode IN (
                'explain_result','compare_scenarios','work_plan','risk_summary','uncertainty','report_narrative'
            )),
            provider TEXT NOT NULL CHECK (provider IN ('deterministic','google_ai')),
            provider_model TEXT,
            status TEXT NOT NULL CHECK (status IN ('completed','completed_with_fallback','failed')),
            conclusion TEXT NOT NULL,
            bullets_json TEXT NOT NULL DEFAULT '[]',
            action_line TEXT NOT NULL,
            full_text TEXT NOT NULL,
            citations_json TEXT NOT NULL DEFAULT '[]',
            source_manifest_json TEXT NOT NULL DEFAULT '[]',
            redaction_summary_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            limitations_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS formal_report_runs (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL REFERENCES decision_support_runs(id) ON DELETE CASCADE,
            narrative_run_id TEXT REFERENCES coco_pilot_runs(id) ON DELETE SET NULL,
            report_format TEXT NOT NULL CHECK (report_format IN ('docx','pdf')),
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_sha256 TEXT NOT NULL CHECK (length(file_sha256) = 64),
            content_fingerprint TEXT NOT NULL CHECK (length(content_fingerprint) = 64),
            generator_version TEXT NOT NULL,
            source_manifest_json TEXT NOT NULL DEFAULT '[]',
            warnings_json TEXT NOT NULL DEFAULT '[]',
            data_notice TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_coco_pilot_analysis
            ON coco_pilot_runs(analysis_run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_coco_pilot_mode
            ON coco_pilot_runs(mode, provider, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_formal_report_analysis
            ON formal_report_runs(analysis_run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_formal_report_fingerprint
            ON formal_report_runs(content_fingerprint, report_format);
        """
    )


def _phase10_schema_down(conn: sqlite3.Connection) -> None:
    for table in ('formal_report_runs', 'coco_pilot_runs'):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="legacy_v211_schema_baseline",
        up=_legacy_schema_up,
        down=_legacy_schema_down,
        fingerprint=LEGACY_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=2,
        name="phase2_normalized_data_foundation",
        up=_phase2_schema_up,
        down=_phase2_schema_down,
        fingerprint=PHASE2_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=3,
        name="phase3_weather_assimilation",
        up=_phase3_schema_up,
        down=_phase3_schema_down,
        fingerprint=PHASE3_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=4,
        name="phase4_production_engine",
        up=_phase4_schema_up,
        down=_phase4_schema_down,
        fingerprint=PHASE4_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=5,
        name="phase5_bayesian_farm_state",
        up=_phase5_schema_up,
        down=_phase5_schema_down,
        fingerprint=PHASE5_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=6,
        name="phase6_pest_risk_inference",
        up=_phase6_schema_up,
        down=_phase6_schema_down,
        fingerprint=PHASE6_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=7,
        name="phase7_intercropping_potential",
        up=_phase7_schema_up,
        down=_phase7_schema_down,
        fingerprint=PHASE7_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=8,
        name="phase8_rehabilitation_scenario_optimization",
        up=_phase8_schema_up,
        down=_phase8_schema_down,
        fingerprint=PHASE8_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=9,
        name="phase9_integrated_decision_support",
        up=_phase9_schema_up,
        down=_phase9_schema_down,
        fingerprint=PHASE9_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
    Migration(
        version=10,
        name="phase10_coco_pilot_formal_reports",
        up=_phase10_schema_up,
        down=_phase10_schema_down,
        fingerprint=PHASE10_SCHEMA_FINGERPRINT,
        destructive_down=True,
    ),
)
