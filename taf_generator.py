"""Experimental TAF-style planning drafts. Never publish as an official TAF."""
from datetime import datetime, timedelta, timezone
import math
import pandas as pd

def build_draft(airport, forecasts, start, duration_hours=24):
    if forecasts.empty:
        return None, ["No numerical forecast guidance is available. Refresh weather first."]
    start = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    now = datetime.now(timezone.utc)
    if start < now - timedelta(hours=1) or start > now + timedelta(hours=30):
        return None, ["Select a start time within the available rolling 30-hour forecast window."]
    end = start + timedelta(hours=duration_hours)
    df = forecasts.copy()
    df["valid_at"] = pd.to_datetime(df["valid_at"], utc=True)
    df = df[(df.valid_at >= pd.Timestamp(start)) & (df.valid_at < pd.Timestamp(end))]
    if df.empty:
        return None, ["No model data for that start time. Refresh and try another hour."]
    lines = [
        "EXPERIMENTAL TAF-STYLE PLANNING DRAFT — NOT VALID FOR OPERATIONAL USE",
        f"Airport: {airport} | Start: {start:%d %b %Y %H:%M} UTC | Requested duration: {duration_hours}h",
        "Model guidance only; NOT an official or complete TAF.",
        "",
    ]
    warnings = [
        "Ceiling height and cloud layers are not forecast by this prototype; total cloud cover is NOT a ceiling.",
        "Weather phenomena, thunderstorms, and TEMPO/BECMG decisions are not validated.",
        "This is a planning outline, not a syntactically valid TAF. Human meteorologist review is required.",
    ]
    slots = 0
    for hour in range(0, duration_hours, 3):
        t = start + timedelta(hours=hour)
        sample = df[(df.valid_at >= pd.Timestamp(t)) & (df.valid_at < pd.Timestamp(t + timedelta(hours=1)))]
        if sample.empty:
            lines.append(f"{t:%d%H%M}Z  MODEL DATA UNAVAILABLE")
            continue
        pivot = sample.pivot_table(index="model", columns="variable", values="value", aggfunc="mean")
        def avg(v):
            if v not in pivot:return None
            x = pivot[v].dropna()
            return float(x.mean()) if not x.empty else None
        speed = avg("wind_speed_10m")
        gust = avg("wind_gusts_10m")
        direction = None
        if "wind_direction_10m" in pivot:
            d = pivot["wind_direction_10m"].dropna()
            if not d.empty:
                angles = [math.radians(float(a)) for a in d]
                direction = (math.degrees(math.atan2(sum(map(math.sin,angles)),sum(map(math.cos,angles))))+360)%360
        wind = "WIND UNAVAILABLE"
        if speed is not None and direction is not None:
            kt = max(0,round(speed/1.852))
            deg = int(round(direction/10)*10)%360
            wind = f"{deg:03d}{kt:02d}KT"
            if gust is not None and gust/1.852 >= kt+5 and gust/1.852 >= 15:
                wind = f"{deg:03d}{kt:02d}G{round(gust/1.852):02d}KT"
        vis = avg("visibility")
        vis_text = "VIS UNAVAILABLE" if vis is None else f"VIS {vis/1609.344:.1f} SM (MODEL)"
        cloud = avg("cloud_cover")
        cloud_text = "CLOUD COVER UNAVAILABLE" if cloud is None else f"TOTAL CLOUD {cloud:.0f}% (NOT CEILING)"
        lines.append(f"{t:%d%H%M}Z  {wind} | {vis_text} | {cloud_text}")
        slots += 1
    if slots == 0:return None, ["No usable model guidance for the requested interval."]
    available_end = df.valid_at.max().to_pydatetime()
    if available_end < end - timedelta(hours=1):
        warnings.append("Model coverage ends before the requested duration; missing intervals are explicitly marked.")
    lines += ["", "MISSING: ceiling/sky layers, weather phenomena, calibrated uncertainty, official TAF change-group logic."]
    return "\n".join(lines), warnings
