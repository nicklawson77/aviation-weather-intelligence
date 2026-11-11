from datetime import datetime,timezone,timedelta
from planning_outline import coverage_category,planning_outline

def test_coverage_is_not_taf_sky():
    assert coverage_category(80)=="BKN-LIKE"
    assert coverage_category(None)=="UNAVAILABLE"
    assert coverage_category(float("nan"))=="UNAVAILABLE"

def test_missing_hours_are_explicit():
    start=datetime(2026,11,10,12,tzinfo=timezone.utc)
    rows=[{"UTC hour":start,"Total (%)":80,"METAR-adjusted total (%)":75,
           "Models reporting total":3}]
    draft=planning_outline(rows,start=start,duration_hours=6)
    assert "NOT AN OFFICIAL TAF" in draft
    assert "NO MODEL GUIDANCE" in draft
    assert "ceiling" in draft.lower()
    assert "BKN-LIKE" in draft

def test_invalid_duration():
    try:planning_outline([],duration_hours=31)
    except ValueError:pass
    else:assert False
