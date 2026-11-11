"""Experimental vertical moisture profile diagnostics.

Relative humidity is not a direct cloud observation. Saturated levels suggest
possible cloud-bearing air, NOT a verified cloud base or aviation ceiling.
"""
LEVELS=(1000,975,950,925,900,850,800,700,600,500)
RH_THRESHOLD=90.0

def saturated_level_candidates(hourly, index, field_elevation_ft, threshold=RH_THRESHOLD):
    """Return possible saturated-layer altitudes in feet AGL.

    Requires paired relative humidity and geopotential height at the same
    pressure level and time. Missing heights are never fabricated.
    """
    candidates=[]
    for pressure in LEVELS:
        rh=hourly.get(f"relative_humidity_{pressure}hPa",[])
        heights=hourly.get(f"geopotential_height_{pressure}hPa",[])
        if index>=len(rh) or index>=len(heights):continue
        if rh[index] is None or heights[index] is None:continue
        try:
            humidity=float(rh[index])
            agl=float(heights[index])*3.28084-float(field_elevation_ft)
        except (TypeError,ValueError):continue
        if humidity>=threshold and agl>=0:
            candidates.append({"pressure_hpa":pressure,
                               "height_ft_agl":round(agl/100)*100,
                               "relative_humidity_pct":round(humidity,1)})
    return sorted(candidates,key=lambda x:x["height_ft_agl"])

def lowest_candidate_ft(candidates):
    """Moist-layer indicator only; NEVER label this an aviation ceiling."""
    return min((x["height_ft_agl"] for x in candidates),default=None)
