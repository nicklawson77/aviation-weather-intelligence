"""Conservative observation nudging for experimental cloud-cover guidance.

METAR cloud layers report sky coverage categories, not exact percentages.
Use broad representative percentages and fade the adjustment to zero by +6h.
Do not infer cloud-base height from cloud-cover percentages.
"""
from datetime import datetime,timezone

COVER_REPRESENTATIVE={"SKC":0.0,"CLR":0.0,"NSC":0.0,"FEW":18.75,"SCT":50.0,"BKN":81.25,"OVC":100.0}

def metar_total_cloud_proxy(metar, layers):
    """Return approximate total coverage only if the observation supports it."""
    if not metar:return None
    raw=str(metar.get("rawOb") or "")
    if "VV" in raw.split():return None
    categories=[x["Coverage"] for x in layers]
    if categories:return max(COVER_REPRESENTATIVE[x] for x in categories if x in COVER_REPRESENTATIVE)
    tokens=raw.split()
    if any(token in ("CLR","SKC","NSC") for token in tokens):return 0.0
    return None

def observation_age_hours(metar,now=None):
    if not metar:return None
    raw=metar.get("obsTime")
    if raw is None:return None
    try:
        if isinstance(raw,(int,float)):observed=datetime.fromtimestamp(raw,timezone.utc)
        else:observed=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        if observed.tzinfo is None:observed=observed.replace(tzinfo=timezone.utc)
        age=((now or datetime.now(timezone.utc))-observed).total_seconds()/3600
        return age if age>=0 else None
    except (ValueError,TypeError,OverflowError):return None

def adjust_cloud_cover(model_pct,observed_proxy_pct,lead_hours,age_hours):
    """Blend toward current observed cloud category, maximum 35% nudge at t=0.

    Returns original model estimate if observation missing/stale or lead >=6h.
    """
    if model_pct is None or observed_proxy_pct is None or age_hours is None:return model_pct
    if age_hours>1.5 or lead_hours<0 or lead_hours>=6:return model_pct
    strength=0.35*(1-lead_hours/6)*max(0,1-age_hours/1.5)
    return round(max(0,min(100,model_pct+strength*(observed_proxy_pct-model_pct))),1)
