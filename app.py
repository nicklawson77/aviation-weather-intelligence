import json, math, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

AIRPORTS={"KDLF":("Laughlin AFB",29.3594,-100.7779),"KAUS":("Austin-Bergstrom",30.1975,-97.6664)}
MODELS={"GFS":"ncep_gfs_seamless","ECMWF IFS":"ecmwf_ifs025","ICON":"icon_seamless"}
FIELDS=["temperature_2m","dew_point_2m","wind_speed_10m","wind_direction_10m","wind_gusts_10m","visibility","cloud_cover","precipitation_probability"]
HEADERS={"User-Agent":"AviationWeatherIntelligenceResearch/0.3"}
DB=Path(__file__).with_name("weather.sqlite3")

def connect():
    c=sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS observations(airport TEXT,observed_at TEXT,raw TEXT,temp REAL,wind_kt REAL,PRIMARY KEY(airport,observed_at,raw));
    CREATE TABLE IF NOT EXISTS forecasts(airport TEXT,model TEXT,fetched_at TEXT,valid_at TEXT,variable TEXT,value REAL,PRIMARY KEY(airport,model,fetched_at,valid_at,variable));
    CREATE TABLE IF NOT EXISTS tafs(airport TEXT,fetched_at TEXT,raw TEXT);
    CREATE TABLE IF NOT EXISTS reviews(airport TEXT,created_at TEXT,draft TEXT,rationale TEXT);
    """)
    return c

def request_json(url,params):
    r=requests.get(url,params=params,headers=HEADERS,timeout=30)
    if r.status_code==204:return []
    r.raise_for_status()
    return r.json()

def asfloat(x):
    try:return float(x)
    except (TypeError,ValueError):return None

def timestamp(v):
    if isinstance(v,(float,int)):return datetime.fromtimestamp(v,timezone.utc).isoformat()
    if not v:return None
    try:return datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:return None

def ingest(c,airport):
    now=datetime.now(timezone.utc).isoformat()
    errors=[]
    metars=[];tafs=[]
    for kind in ("metar","taf"):
        try:
            data=request_json("https://aviationweather.gov/api/data/"+kind,{"ids":airport,"format":"json"})
            if not isinstance(data,list):data=[]
            if kind=="metar":metars=data
            else:tafs=data
        except Exception as e:errors.append(kind+": "+str(e))
    for m in metars:
        raw=m.get("rawOb") or json.dumps(m)
        observed=timestamp(m.get("obsTime"))
        if observed:
            c.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?)",
                      (airport,observed,raw,asfloat(m.get("temp")),asfloat(m.get("wspd"))))
    for t in tafs:
        c.execute("INSERT INTO tafs VALUES(?,?,?)",(airport,now,t.get("rawTAF") or json.dumps(t)))
    for name,code in MODELS.items():
        try:
            data=request_json("https://api.open-meteo.com/v1/forecast",{
                "latitude":AIRPORTS[airport][1],"longitude":AIRPORTS[airport][2],
                "hourly":",".join(FIELDS),"models":code,"forecast_days":2,"timezone":"UTC"})
            hourly=data.get("hourly",{})
            for i,t in enumerate(hourly.get("time",[])):
                valid=timestamp(t+"+00:00")
                if not valid:continue
                hours=(datetime.fromisoformat(valid)-datetime.fromisoformat(now)).total_seconds()/3600
                if hours < -1 or hours > 30:continue
                for field in FIELDS:
                    values=hourly.get(field,[])
                    v=asfloat(values[i]) if i<len(values) else None
                    if v is not None:
                        c.execute("INSERT OR IGNORE INTO forecasts VALUES(?,?,?,?,?,?)",
                                  (airport,name,now,valid,field,v))
        except Exception as e:errors.append(name+": "+str(e))
    c.commit()
    return metars,tafs,errors

def latest_forecasts(c,airport):
    return pd.read_sql_query("""
    SELECT f.* FROM forecasts f JOIN
    (SELECT model,MAX(fetched_at) AS newest FROM forecasts WHERE airport=? GROUP BY model) r
    ON f.model=r.model AND f.fetched_at=r.newest WHERE f.airport=?
    """,c,params=(airport,airport))

def verification(c,airport):
    obs=pd.read_sql_query("SELECT * FROM observations WHERE airport=?",c,params=(airport,))
    forecasts=pd.read_sql_query("SELECT * FROM forecasts WHERE airport=? AND variable IN ('temperature_2m','wind_speed_10m')",c,params=(airport,))
    if obs.empty or forecasts.empty:return pd.DataFrame()
    rows=[]
    obs["observed_at"]=pd.to_datetime(obs.observed_at,utc=True)
    forecasts["valid_at"]=pd.to_datetime(forecasts.valid_at,utc=True)
    forecasts["fetched_at"]=pd.to_datetime(forecasts.fetched_at,utc=True)
    for _,o in obs.iterrows():
        for var,observed in [("temperature_2m",o["temp"]),("wind_speed_10m",o["wind_kt"]*1.852 if pd.notna(o["wind_kt"]) else None)]:
            if pd.isna(observed):continue
            f=forecasts[(forecasts.variable==var)&(forecasts.fetched_at<=o.observed_at)].copy()
            if f.empty:continue
            f["minutes"]=(f.valid_at-o.observed_at).abs().dt.total_seconds()/60
            f=f[f.minutes<=35]
            if f.empty:continue
            for model,g in f.groupby("model"):
                best=g.sort_values(["minutes","fetched_at"],ascending=[True,False]).iloc[0]
                lead=(best.valid_at-best.fetched_at).total_seconds()/3600
                rows.append({"Model":model,"Variable":var,"Lead (h)":round(lead,1),
                             "Absolute error":abs(float(best.value)-float(observed)),
                             "Observation":o.observed_at})
    return pd.DataFrame(rows)

st.set_page_config(page_title="Aviation Weather Intelligence",page_icon="✈️",layout="wide")
st.title("✈️ Aviation Weather Intelligence")
st.caption("30-hour experimental aviation forecast dashboard · not an official TAF service")
airport=st.sidebar.selectbox("Airport",list(AIRPORTS),format_func=lambda a:a+" — "+AIRPORTS[a][0])
c=connect()
if st.sidebar.button("Refresh live weather",type="primary"):
    with st.spinner("Collecting METAR, TAF and model forecasts..."):
        metars,tafs,errors=ingest(c,airport)
        st.session_state["errors_"+airport]=errors
        st.session_state["last_"+airport]=datetime.now(timezone.utc).isoformat()
st.subheader(airport+" — "+AIRPORTS[airport][0])
st.caption("Last refresh: "+st.session_state.get("last_"+airport,"Not refreshed this session"))
obs=pd.read_sql_query("SELECT * FROM observations WHERE airport=? ORDER BY observed_at DESC LIMIT 1",c,params=(airport,))
taf=pd.read_sql_query("SELECT * FROM tafs WHERE airport=? ORDER BY fetched_at DESC LIMIT 1",c,params=(airport,))
left,right=st.columns(2)
with left:
    st.markdown("#### Latest archived METAR")
    if obs.empty:st.info("No airport METAR yet. No nearby station is substituted.")
    else:
        st.code(obs.iloc[0]["raw"])
        st.caption("Observed: "+obs.iloc[0]["observed_at"])
with right:
    st.markdown("#### Latest archived official TAF")
    if taf.empty:st.info("No TAF available.")
    else:st.code(taf.iloc[0]["raw"])
st.markdown("### 30-hour multi-model forecast")
f=latest_forecasts(c,airport)
if f.empty:st.info("Press Refresh live weather to load model guidance.")
else:
    variable=st.selectbox("Forecast variable",FIELDS)
    selected=f[f.variable==variable].copy()
    selected["valid_at"]=pd.to_datetime(selected.valid_at,utc=True)
    st.line_chart(selected.pivot_table(index="valid_at",columns="model",values="value"))
    st.dataframe(selected[["model","valid_at","value"]],hide_index=True,use_container_width=True)
st.markdown("### Forecast verification")
scores=verification(c,airport)
if scores.empty:st.info("Collect multiple refreshes over time to match past forecasts against subsequent METARs.")
else:
    summary=scores.groupby(["Model","Variable"]).agg(MAE=("Absolute error","mean"),Cases=("Absolute error","count")).reset_index()
    st.dataframe(summary,hide_index=True,use_container_width=True)
    st.caption("Preliminary scoring: only forecasts collected before observations, matched within 35 minutes. Not yet calibrated.")
st.markdown("### Internal TAF review workspace")
st.warning("Human-reviewed drafts only. This app does not issue or automatically amend official TAFs.")
with st.form("review"):
    draft=st.text_area("Draft TAF text",value=taf.iloc[0]["raw"] if not taf.empty else "",height=110)
    rationale=st.text_area("Review rationale")
    if st.form_submit_button("Save internal review"):
        if draft.strip():
            c.execute("INSERT INTO reviews VALUES(?,?,?,?)",(airport,datetime.now(timezone.utc).isoformat(),draft,rationale))
            c.commit();st.success("Saved review record.")
        else:st.error("Enter draft text.")
with st.expander("Data feed errors"):
    st.write(st.session_state.get("errors_"+airport,[]))
st.caption("Research tool only. Use approved official aviation sources for operational flight decisions.")
c.close()
