from datetime import datetime,timezone,timedelta
from cloud_observation import adjust_cloud_cover,observation_age_hours,metar_total_cloud_proxy

def test_cloud_nudge():
    assert adjust_cloud_cover(70,None,0,0)==70
    assert adjust_cloud_cover(70,100,6,0)==70
    assert adjust_cloud_cover(70,100,0,3)==70
    assert 70<adjust_cloud_cover(70,100,0,0)<100

def test_metar_proxy():
    assert metar_total_cloud_proxy({"rawOb":"KDLF 101200Z 00000KT 10SM CLR 20/10 A3000"},[])==0
    assert metar_total_cloud_proxy({"rawOb":"KDLF 101200Z 00000KT 10SM BKN025 20/10 A3000"},[{"Coverage":"BKN","Base (ft AGL)":2500}])==81.25
    assert metar_total_cloud_proxy({"rawOb":"KDLF 101200Z 00000KT 10SM 20/10 A3000"},[]) is None

def test_observation_age():
    now=datetime(2026,11,10,12,tzinfo=timezone.utc)
    assert observation_age_hours({"obsTime":"2026-11-10T11:30:00Z"},now)==0.5
