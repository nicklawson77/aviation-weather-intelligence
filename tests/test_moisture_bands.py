from moisture_bands import moisture_bands

def test_separated_moist_layers():
    levels=[
        {"height_ft_agl":1000,"relative_humidity_pct":92},
        {"height_ft_agl":2000,"relative_humidity_pct":95},
        {"height_ft_agl":9000,"relative_humidity_pct":94},
    ]
    bands=moisture_bands(levels)
    assert len(bands)==2
    assert bands[0]["base_indicator_ft_agl"]==1000
    assert bands[0]["top_indicator_ft_agl"]==2000
    assert bands[1]["sampled_levels"]==1

def test_empty():
    assert moisture_bands([])==[]
