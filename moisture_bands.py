"""Group saturated pressure levels into *possible* cloud-bearing layers.

These are moisture-profile diagnostics, not aviation cloud-layer forecasts.
They must never be encoded as FEW/SCT/BKN/OVC or TAF ceilings.
"""
from vertical_profile import saturated_level_candidates

def moisture_bands(candidates, max_gap_ft=2500):
    """Group vertically adjacent moist levels and return tentative AGL bands."""
    ordered=sorted(
        (c for c in candidates if c.get("height_ft_agl") is not None),
        key=lambda c:c["height_ft_agl"])
    if not ordered:return []
    groups=[[ordered[0]]]
    for c in ordered[1:]:
        if c["height_ft_agl"]-groups[-1][-1]["height_ft_agl"]<=max_gap_ft:
            groups[-1].append(c)
        else:
            groups.append([c])
    return [
        {"base_indicator_ft_agl":g[0]["height_ft_agl"],
         "top_indicator_ft_agl":g[-1]["height_ft_agl"],
         "sampled_levels":len(g),
         "mean_rh_pct":round(sum(x["relative_humidity_pct"] for x in g)/len(g),1)}
        for g in groups
    ]

def hourly_moisture_bands(hourly,index,elevation_ft):
    return moisture_bands(saturated_level_candidates(hourly,index,elevation_ft))
