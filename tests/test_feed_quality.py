from feed_quality import model_field_status

def test_complete():
    x=model_field_status({"time":["2026-11-10T12:00"],"cloud_cover":[50]},["cloud_cover"])
    assert x["status"]=="complete"

def test_partial():
    x=model_field_status({"time":["2026-11-10T12:00"],"cloud_cover":[50],"cloud_cover_low":[None]},["cloud_cover","cloud_cover_low"])
    assert x["status"]=="partial"
    assert x["missing"]==["cloud_cover_low"]

def test_empty():
    x=model_field_status({},["cloud_cover"])
    assert x["status"]=="unavailable"
