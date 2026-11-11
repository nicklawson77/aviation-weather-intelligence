"""Cloud-layer and ceiling utilities for the experimental aviation dashboard.

Only construct forecast layers from explicit layer coverage + base height pairs.
Do not infer a ceiling from total cloud cover or a surface dewpoint spread.
"""
from dataclasses import dataclass
from statistics import median
from typing import Optional

CODES=("SKC","FEW","SCT","BKN","OVC")

@dataclass(frozen=True)
class Layer:
    coverage_pct: float
    base_ft_agl: float
    source: str = "model"

    @property
    def oktas(self):
        return max(0,min(8,round(self.coverage_pct*8/100)))

    @property
    def category(self):
        p=self.coverage_pct
        if p<6.25:return "SKC"
        if p<31.25:return "FEW"
        if p<68.75:return "SCT"
        if p<93.75:return "BKN"
        return "OVC"

def ceiling_ft(layers):
    """Lowest BKN/OVC layer base, or None if not present."""
    values=[x.base_ft_agl for x in layers if x.category in ("BKN","OVC")]
    return min(values) if values else None

def blend_layers(model_layers, weights=None):
    """Blend layer estimates by matching altitude bands, not raw layer positions.

    model_layers: mapping model -> list[Layer]. Missing models do not vote clear.
    Each altitude band needs at least one explicitly supplied layer.
    Returns experimental layers and model support counts.
    """
    if weights is None:weights={name:1.0 for name in model_layers}
    bands=[(0,2000),(2000,6000),(6000,12000),(12000,25000),(25000,60000)]
    out=[]
    for low,high in bands:
        records=[]
        for name,layers in model_layers.items():
            matches=[x for x in layers if low<=x.base_ft_agl<high]
            if matches:
                strongest=max(matches,key=lambda x:x.coverage_pct)
                w=max(0.0,float(weights.get(name,0.0)))
                if w>0:records.append((strongest,w))
        if not records:continue
        total=sum(w for _,w in records)
        coverage=sum(x.coverage_pct*w for x,w in records)/total
        height=sum(x.base_ft_agl*w for x,w in records)/total
        out.append({"layer":Layer(round(coverage,1),round(height/100)*100,"blended_model"),
                    "models_reporting":len(records),"models_available":len(model_layers)})
    return out

def metar_ceiling_adjustment(forecast_ceiling_ft, observed_ceiling_ft, lead_hours,
                             confidence=0.5):
    """Bounded, decaying near-term ceiling correction (experimental).

    Only adjust when BOTH forecast and observation have measured/derived ceilings.
    A missing ceiling is not the same as unlimited.
    """
    if forecast_ceiling_ft is None or observed_ceiling_ft is None:return forecast_ceiling_ft
    if lead_hours<0:return forecast_ceiling_ft
    strength=max(0,min(0.65,float(confidence)))*max(0,1-lead_hours/6)
    return round((forecast_ceiling_ft+strength*(observed_ceiling_ft-forecast_ceiling_ft))/100)*100
