"""KDLF-only cloud dashboard prototype.

Run with: streamlit run cloud_dashboard.py
The deployed app.py on main is deliberately unchanged.
"""
from datetime import datetime, timezone
import re
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from station_config import active_station

STATION=active_station()
MODELS={"GFS":"ncep_gfs_seamless","ECMWF IFS":"ecmwf_ifs025","ICON":"icon_seamless"}
CLOUD_FIELDS=["cloud_cover","cloud_cover_low","cloud_cover_mid","cloud_cover_high"]
HEADERS={"User-Agent":"AviationWeatherIntelligenceResearch/0.4"}

def fetch(url,params):
    response=requests.get(url,params=params,headers=HEADERS,timeout=25)
    response.raise_for_status()
    return response.json()

@st.cache_data(ttl=900,show_spinner=False)
def model_data():
    records=[]
    errors=[]
    for name,model in MODELS.items():
        try:
            data=fetch("https://api.open-meteo.com/v1/forecast",{
                "latitude":STATION["latitude"],"longitude":STATION["longitude"],
                "models":model,"hourly":",".join(CLOUD_FIELDS),
                "forecast_days":2,"timezone":"UTC"})
            hourly=data.get("hourly",{})
            times=hourly.get("time",[])
            for i,t in enumerate(times):
                record={"valid_at":pd.to_datetime(t,utc=True),"model":name}
                for field in CLOUD_FIELDS:
                    values=hourly.get(field,[])
                    record[field]=values[i] if i<len(values) else None
                records.append(record)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    return pd.DataFrame(records),errors

@st.cache_data(ttl=300,show_spinner=False)
def metar_data():
    data=fetch("https://aviationweather.gov/api/data/metar",
               {"ids":"KDLF","format":"json","hours":3})
    if not isinstance(data,list):return None
    return data[0] if data else None

def observed_layers(metar):
    """Extract only explicitly reported METAR cloud layers."""
    layers=[]
    if not metar:return layers
    for item in metar.get("clouds",[]) or []:
        cover=str(item.get("cover","")).upper()
        base=item.get("base")
        if cover in ("FEW","SCT","BKN","OVC") and base is not None:
            layers.append({"Coverage":cover,"Base (ft AGL)":base,"Source":"Observed METAR"})
    if layers:return layers
    raw=metar.get("rawOb","")
    for cover,hundreds in re.findall(r"\b(FEW|SCT|BKN|OVC)(\d{3})(?:CB|TCU)?\b",raw):
        layers.append({"Coverage":cover,"Base (ft AGL)":int(hundreds)*100,"Source":"Observed METAR"})
    return layers

def observed_ceiling(layers):
    heights=[x["Base (ft AGL)"] for x in layers if x["Coverage"] in ("BKN","OVC")]
    return min(heights) if heights else None

st.set_page_config(page_title="KDLF Cloud Intelligence",page_icon="☁️",layout="wide")
st.title("☁️ KDLF Cloud Intelligence")
st.caption("Development prototype · experimental model guidance, not an official aviation forecast")
st.info("Model cloud coverage is available. Model cloud-base heights and FEW/SCT/BKN/OVC layers are not yet available from these feeds; they are intentionally NOT fabricated.")
if st.button("Refresh observations and models"):
    model_data.clear()
    metar_data.clear()
try:
    metar=metar_data()
except Exception as exc:
    metar=None
    st.warning(f"METAR feed unavailable: {exc}")
if metar:
    st.subheader("Latest KDLF observation")
    st.code(metar.get("rawOb","Raw report unavailable"))
    layers=observed_layers(metar)
    if layers:
        st.dataframe(pd.DataFrame(layers),hide_index=True,use_container_width=True)
        ceiling=observed_ceiling(layers)
        st.metric("Observed ceiling",f"{ceiling:,} ft AGL" if ceiling is not None else "No BKN/OVC layer reported")
    else:
        st.caption("No explicit cloud layers parsed from this METAR. Ceiling unavailable.")
else:
    st.warning("No KDLF METAR returned; no nearby station is substituted.")

st.subheader("Hourly model cloud coverage — next 30 hours")
df,errors=model_data()
now=pd.Timestamp.now(tz="UTC")
if df.empty:
    st.error("No model cloud guidance is available.")
else:
    df=df[(df.valid_at>=now.floor("h"))&(df.valid_at<=now+pd.Timedelta(hours=30))].copy()
    coverage=st.selectbox("Cloud category",CLOUD_FIELDS,format_func=lambda x:{
        "cloud_cover":"Total cloud cover","cloud_cover_low":"Low clouds",
        "cloud_cover_mid":"Middle clouds","cloud_cover_high":"High clouds"}[x])
    graph=df[["valid_at","model",coverage]].dropna()
    if not graph.empty:
        fig=px.line(graph,x="valid_at",y=coverage,color="model",markers=True)
        fig.update_yaxes(range=[0,100],title="Cloud cover (%)")
        fig.update_xaxes(title="Valid time (UTC)")
        st.plotly_chart(fig,use_container_width=True)
    summary=df.groupby("valid_at",as_index=False)[CLOUD_FIELDS].mean(numeric_only=True)
    summary=summary.rename(columns={
        "valid_at":"UTC hour","cloud_cover":"Total (%)",
        "cloud_cover_low":"Low (%)","cloud_cover_mid":"Mid (%)",
        "cloud_cover_high":"High (%)"})
    summary["Forecast cloud layers"]="Unavailable — vertical cloud-base data required"
    summary["Forecast ceiling (ft AGL)"]="Unavailable"
    st.dataframe(summary,hide_index=True,use_container_width=True)
    st.caption("Current blend: unweighted mean of available models. METAR is displayed as independent observation; no cloud-cover adjustment is applied until a validated method exists.")
if errors:
    with st.expander("Model feed errors"):
        for err in errors:st.write(err)
st.caption("Research use only. Verify operational conditions using approved aviation weather products.")
