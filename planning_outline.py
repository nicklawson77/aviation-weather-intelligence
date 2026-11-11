"""Conservative forecast summary for KDLF planning, not a TAF.

Cloud-cover percentages can indicate broad sky coverage, but never imply
specific cloud bases or an aviation ceiling without appropriate model data.
"""
from datetime import datetime, timezone, timedelta
import math

def coverage_category(pct):
    if pct is None:return "UNAVAILABLE"
    try:
        value=float(pct)
        if not math.isfinite(value) or not 0<=value<=100:return "UNAVAILABLE"
    except (ValueError,TypeError):return "UNAVAILABLE"
    if value<6.25:return "SKC-LIKE"
    if value<31.25:return "FEW-LIKE"
    if value<68.75:return "SCT-LIKE"
    if value<93.75:return "BKN-LIKE"
    return "OVC-LIKE"

def planning_outline(rows,station="KDLF",start=None,duration_hours=24):
    """Return plain-language 3-hour snapshots; never TAF syntax."""
    if not isinstance(duration_hours,int) or not 1<=duration_hours<=30:
        raise ValueError("Duration must be 1–30 hours.")
    if start is None:start=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    if start.tzinfo is None:raise ValueError("Start must be timezone-aware.")
    start=start.astimezone(timezone.utc)
    indexed={}
    for row in rows:
        when=row.get("UTC hour")
        if hasattr(when,"to_pydatetime"):when=when.to_pydatetime()
        if isinstance(when,datetime) and when.tzinfo is not None:
            indexed[when.astimezone(timezone.utc).replace(minute=0,second=0,microsecond=0)]=row
    lines=["EXPERIMENTAL PLANNING OUTLINE — NOT AN OFFICIAL TAF",
           f"{station} | {start:%Y-%m-%d %H:%M} UTC | {duration_hours}h",
           "Coverage categories describe TOTAL cloud fraction only, not a layer or ceiling.",
           "Cloud-base heights, aviation ceilings, visibility and wind are NOT provided here.",""]
    for offset in range(0,duration_hours,3):
        when=start+timedelta(hours=offset)
        row=indexed.get(when)
        if row is None:
            lines.append(f"{when:%d%H%M}Z | NO MODEL GUIDANCE")
            continue
        cover=row.get("METAR-adjusted total (%)")
        if cover is None or (isinstance(cover,float) and not math.isfinite(cover)):
            cover=row.get("Total (%)")
        category=coverage_category(cover)
        if category=="UNAVAILABLE":detail="CLOUD GUIDANCE UNAVAILABLE"
        else:
            count=row.get("Models reporting total",0)
            detail=f"TOTAL CLOUD {float(cover):.0f}% ({category}); {count} model(s)"
        lines.append(f"{when:%d%H%M}Z | {detail}")
    lines.append("")
    lines.append("Research only. Consult approved METARs, TAFs and operational weather products.")
    return "\n".join(lines)
