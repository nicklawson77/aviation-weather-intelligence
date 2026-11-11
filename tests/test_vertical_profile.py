from vertical_profile import saturated_level_candidates,lowest_candidate_ft

def test_missing_heights_are_not_invented():
    hourly={"relative_humidity_925hPa":[95]}
    assert saturated_level_candidates(hourly,0,1000)==[]
    assert lowest_candidate_ft([]) is None

def test_saturated_pressure_level_agl():
    hourly={"relative_humidity_925hPa":[96],
            "geopotential_height_925hPa":[700]}
    levels=saturated_level_candidates(hourly,0,1000)
    assert len(levels)==1
    assert levels[0]["height_ft_agl"]==1300

def test_dry_levels_excluded():
    hourly={"relative_humidity_925hPa":[60],
            "geopotential_height_925hPa":[700]}
    assert saturated_level_candidates(hourly,0,1000)==[]
