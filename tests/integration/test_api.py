from fastapi.testclient import TestClient
from app.main import app
from app.schemas.farm import FarmCreate

client=TestClient(app)


def test_health_and_config():
    assert client.get('/api/health').status_code==200
    config = client.get('/api/config').json()
    assert config['development_data_mode'] is True
    assert config['official_data_mode'] is True
    assert 'PSA' in config['data_notice']


def test_farm_crud():
    payload=FarmCreate().model_dump(mode='json')
    created=client.post('/api/farms',json=payload)
    assert created.status_code==201
    farm_id=created.json()['id']
    assert client.get(f'/api/farms/{farm_id}').status_code==200
    payload['name']='Updated Farm'
    assert client.put(f'/api/farms/{farm_id}',json=payload).json()['name']=='Updated Farm'
    assert client.delete(f'/api/farms/{farm_id}').status_code==200
    assert client.get(f'/api/farms/{farm_id}').status_code==404


def test_pest_suitability_and_simulation_endpoints():
    pest=client.post('/api/pest-risk/evaluate',json={}).json()
    assert 0 <= pest['posterior_probability'] <= 1
    suit=client.post('/api/suitability/evaluate',json={}).json()
    assert 0 <= suit['score'] <= 1
    sim=client.post('/api/simulation/run',json={'runs':100,'end_year':2030}).json()
    assert sim['summary']['final_median_tons'] >= 0


def test_climate_and_rehab_endpoints():
    assert len(client.post('/api/climate/projection',json={}).json()['monthly'])==12
    farm=FarmCreate().model_dump(mode='json')
    grid=client.post('/api/rehabilitation-map?rows=3&cols=3',json=farm).json()
    assert len(grid['cells'])==9


def test_full_analysis_and_report_generation():
    response=client.post('/api/analysis/full',json={'runs':100,'end_year':2030})
    assert response.status_code==200
    result=response.json(); assert result['analysis_id']
    report=client.post('/api/reports/generate',json={'analysis_id':result['analysis_id']})
    assert report.status_code==200
    download=client.get(report.json()['download_url'])
    assert download.status_code==200
    assert download.headers['content-type']=='application/pdf'


def test_invalid_tree_totals_are_rejected():
    payload=FarmCreate().model_dump(mode='json')
    payload['trees']['productive'] += 1
    assert client.post('/api/farms',json=payload).status_code==422


def test_unknown_model_returns_404():
    assert client.get('/api/models/not-a-model').status_code == 404


def test_scenario_comparison_contract_is_compact():
    response = client.post('/api/scenarios/compare', json={'runs': 100, 'end_year': 2030})
    assert response.status_code == 200
    data = response.json()
    assert data['recommended_simulation']['intervention'] == data['recommended_intervention']
    assert all('simulation' not in row for row in data['ranking'])


def test_static_fallback_does_not_expose_files_outside_static():
    response = client.get('/../app/main.py')
    assert response.status_code == 200
    assert 'from fastapi import FastAPI' not in response.text
    assert '<!doctype html>' in response.text.lower()


def test_offline_mode_blocks_live_weather_but_keeps_core_analysis(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'offline_mode', True)
    weather = client.post('/api/weather/point', json={'latitude': 6.3, 'longitude': 125})
    assert weather.status_code == 503
    simulation = client.post('/api/simulation/run', json={'runs': 100, 'end_year': 2030})
    assert simulation.status_code == 200


def test_embedded_weather_viewer_and_hybrid_farm_site_endpoint(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.api import routes

    times = [(datetime(2026, 7, 19, tzinfo=timezone.utc) + timedelta(hours=i)).isoformat() for i in range(48)]
    points = 36
    cube = {
        'rows': 6, 'cols': 6, 'west': 123.5, 'east': 126.5, 'south': 5.0, 'north': 8.0,
        'latitudes': [8.0, 7.4, 6.8, 6.2, 5.6, 5.0],
        'longitudes': [123.5, 124.1, 124.7, 125.3, 125.9, 126.5],
        'times': times,
        'values': {},
        'metadata': {'source': 'Mock model', 'source_type': 'Deterministic forecast', 'is_stale': False},
    }
    for variable, value in {
        'precipitation': 0.5, 'temperature_2m': 28.0, 'cloud_cover': 80.0,
        'pressure_msl': 1008.0, 'wind_speed_10m': 12.0,
        'wind_direction_10m': 90.0, 'relative_humidity_2m': 84.0,
    }.items():
        cube['values'][variable] = [[value for _ in times] for __ in range(points)]

    async def mocked_cube(_request):
        return cube

    monkeypatch.setattr(routes, 'weather_cube', mocked_cube)
    viewer = client.get('/weather-viewer')
    assert viewer.status_code == 200
    assert 'Animated rain intensity' in viewer.text
    assert client.get('/static/weather-viewer/app.js').status_code == 200

    payload = {
        'farm': FarmCreate().model_dump(mode='json'),
        'start_year': 2026,
        'end_year': 2027,
        'start_date': '2026-07-19',
        'runs': 100,
        'include_live_short_term': True,
    }
    response = client.post('/api/farm-site/forecast', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['frames'][0]['data_mode'] == 'deterministic_short_term_forecast'
    assert data['frames'][0]['spatial_grid']
    assert data['short_term_live_merge']['available'] is True


def test_official_data_and_database_forecast_endpoints():
    summary = client.get('/api/official-data/summary')
    assert summary.status_code == 200
    assert summary.json()['source'] == 'Philippine Statistics Authority (PSA)'
    profile = client.get('/api/official-data/profile?province=South%20Cotabato').json()
    assert profile['products']['coconut_w_husk']['latest_official_2025_tons'] > 0
    payload = {
        'name': 'Integration forecast',
        'summary': {'weeks': 10, 'scenario': 'ssp245'},
        'forecast': {'frames': [{'week_start': '2026-01-01'}]},
    }
    saved = client.post('/api/database/forecasts', json=payload)
    assert saved.status_code == 201
    identifier = saved.json()['forecast_id']
    assert client.get(f'/api/database/forecasts/{identifier}').json()['name'] == 'Integration forecast'
    assert client.get('/api/database/summary').json()['forecasts'] == 1
    assert client.delete(f'/api/database/forecasts/{identifier}').status_code == 200


def test_docx_report_and_supplemental_weekly_outlook():
    analysis = client.post('/api/analysis/full', json={'runs': 100, 'end_year': 2030}).json()
    supplement = {
        'farm_site_forecast': {
            'effective_start_date': '2026-07-19', 'effective_end_date': '2030-12-31',
            'timeline_resolution': 'weekly', 'scenario': 'ssp245',
            'intervention': 'combined_rehabilitation',
            'posterior_summary': {'final_median_tons': 17.2},
            'annual_by_product': [{'year': 2030, 'coconut_w_husk_tons': 17.2, 'coconut_mature_tons': 16.8, 'coconut_young_tons': .4}],
            'extreme_events': [{'label': 'Heat stress', 'start_date': '2028-03-01', 'end_date': '2028-03-14', 'peak_severity': .6, 'estimated_production_loss_tons': .2}],
        }
    }
    report = client.post('/api/reports/generate', json={'analysis_id': analysis['analysis_id'], 'analysis': supplement, 'report_format': 'docx'})
    assert report.status_code == 200
    downloaded = client.get(report.json()['download_url'])
    assert downloaded.status_code == 200
    assert downloaded.headers['content-type'].startswith('application/vnd.openxmlformats-officedocument')
    assert downloaded.content.startswith(b'PK')


def test_database_rejects_oversized_forecast_timeline():
    payload = {
        'name': 'Too many frames',
        'summary': {},
        'forecast': {'frames': [{'week_start': '2026-01-01'} for _ in range(2501)]},
    }
    response = client.post('/api/database/forecasts', json=payload)
    assert response.status_code == 422
    assert 'maximum is 2500' in response.text
