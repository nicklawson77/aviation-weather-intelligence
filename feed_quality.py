"""Forecast feed quality checks; do not silently count missing model data."""
from datetime import datetime, timezone

def model_field_status(hourly, requested_fields):
    times=hourly.get("time") or []
    if not times:
        return {"status":"unavailable","hours":0,"available":[],"missing":list(requested_fields)}
    available=[]
    missing=[]
    for field in requested_fields:
        values=hourly.get(field)
        if isinstance(values,list) and any(v is not None for v in values):
            available.append(field)
        else:
            missing.append(field)
    return {"status":"complete" if not missing else ("partial" if available else "unavailable"),
            "hours":len(times),"available":available,"missing":missing}

def valid_model_count(frame, field, time_column="valid_at", model_column="model"):
    """Return per-hour count of models actually reporting the selected field."""
    if frame.empty or field not in frame.columns:return {}
    subset=frame.dropna(subset=[field])
    return subset.groupby(time_column)[model_column].nunique().to_dict()
