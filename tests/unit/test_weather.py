import pytest
from app.weather.providers import parse_gdacs_rss
from app.schemas.weather import WeatherGridRequest


def test_gdacs_parser_filters_tropical_cyclones():
    xml='''<rss xmlns:georss="http://www.georss.org/georss"><channel><item><title>Tropical Cyclone TEST</title><category>TC</category><category>ORANGE</category><georss:point>10 125</georss:point><guid>x</guid></item><item><title>Flood</title><category>FL</category></item></channel></rss>'''
    events=parse_gdacs_rss(xml)
    assert len(events)==1 and events[0]['latitude']==10


def test_weather_grid_validation():
    with pytest.raises(Exception):
        WeatherGridRequest(west=125,south=7,east=124,north=8)
