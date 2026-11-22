import streamlit as st
import pandas as pd
import requests, sqlite3, json, os
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
DB = BASE / 'highway_watch.db'
ROUTES = {
'Quetta–Karachi (N-25)': {'code':'N-25','distance':'688 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Mastung',29.7997,66.8455,'1,701m'),('Kalat',29.0266,66.5936,'2,007m'),('Surab',28.4914,66.2585,'1,750m'),('Khuzdar',27.8,66.6167,'1,237m'),('Wadh',27.3436,66.3708,'1,220m'),('Lasbela',26.2289,66.3106,'87m'),('Hub',25.0244,66.8906,'24m')], 'alt':'Quetta → Sibi (N-65) → Jacobabad → Sukkur → Karachi','reason':'Low-elevation alternative; verify road status with authorities before travel.'},
'Quetta–Zhob (N-50)': {'code':'N-50','distance':'331 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Kuchlak',30.3125,67.0114,'1,560m'),('Khan Mehtarzai',30.4833,67.6167,'2,224m'),('Muslim Bagh',30.8317,67.7408,'1,787m'),('Qilla Saifullah',30.7,68.36,'1,550m'),('Zhob',31.3411,69.4481,'1,426m')], 'alt':'Quetta → Ziarat Cross → Loralai → Mekhtar → Zhob','reason':'Alternative corridor; confirm local conditions before departure.'},
'Quetta–Sibi (N-65)': {'code':'N-65','distance':'163 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Kolpur (Bolan Pass)',29.9,67.15,'1,790m'),('Mach',29.8637,67.3302,'1,006m'),('Dhadar',29.4749,67.6514,'132m'),('Sibi',29.543,67.8773,'130m')], 'alt':'Quetta → Harnai → Shahrag → Sibi','reason':'Alternative only when confirmed safe and open.'},
'Quetta–Chaman (N-25 North)': {'code':'N-25N','distance':'125 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Kuchlak',30.3125,67.0114,'1,560m'),('Khojak Pass',30.805,66.568,'2,290m'),('Chaman',30.9177,66.4526,'1,338m')], 'alt':'Quetta → Kuchlak → Pishin → Gulistan → Chaman','reason':'Check pass conditions and official clearance.'},
'Quetta–Nushki–Taftan (N-40)': {'code':'N-40','distance':'610 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Lakpass',29.965,66.82,'1,810m'),('Nushki',29.5522,66.0215,'1,020m'),('Dalbandin',28.8885,64.4062,'843m'),('Nok Kundi',28.8261,62.7489,'680m'),('Taftan',28.9667,61.5833,'910m')], 'alt':'Route alternative depends on current closures and authority advice.','reason':'Long desert corridor; check fuel, heat and wind conditions.'},
'Quetta–Loralai–DG Khan (N-70)': {'code':'N-70','distance':'425 km','points':[('Quetta',30.1798,66.975,'1,680m'),('Ziarat Cross',30.3824,67.7256,'2,450m'),('Sanjawi',30.2856,68.3489,'1,620m'),('Loralai',30.3705,68.5979,'1,430m'),('Rakhni',30.0683,69.9214,'1,110m')], 'alt':'Quetta → Sibi (N-65) → Jacobabad → Kashmore → Rajanpur','reason':'Confirm the alternate road is open before using it.'}}
LANGS=['Urdu','English','Pashto','Balochi']

def db():
    c=sqlite3.connect(DB, check_same_thread=False)
    c.execute('''CREATE TABLE IF NOT EXISTS drivers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,vehicle TEXT,plate TEXT,route TEXT,language TEXT,sector TEXT,created TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,route TEXT,severity TEXT,language TEXT,message TEXT,channel TEXT,created TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS roads(id INTEGER PRIMARY KEY AUTOINCREMENT,route TEXT,area TEXT,status TEXT,note TEXT,updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sos(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,driver TEXT,route TEXT,sector TEXT,kind TEXT,details TEXT,status TEXT,created TEXT)''')
    c.commit(); return c
conn=db()
st.set_page_config(page_title='Highway Watch | Balochistan',page_icon='🛣️',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
:root{color-scheme:dark} .stApp{background:#070c14;color:#e7edf5}.block-container{padding-top:1.4rem;max-width:1500px}
[data-testid="stSidebar"]{background:#0b121e;border-right:1px solid #1e293b}.stMetric{background:#0e1928;border:1px solid #1e3043;padding:15px;border-radius:13px}
div[data-testid="stVerticalBlock"] div.stButton>button{border-radius:10px;border:1px solid #244052;background:#102132;color:#e8f4f7}
div[data-testid="stForm"]{background:#0c1725;border:1px solid #1e3448;border-radius:12px;padding:16px}
.hw-card{background:#0e1928;border:1px solid #203348;border-radius:14px;padding:17px;margin-bottom:10px}
.hw-muted{color:#91a4b9;font-size:12px}.hw-green{color:#34d399}.hw-title{font-size:27px;font-weight:750;color:#f4f8fb}.hw-sub{color:#91a4b9;margin-top:2px}
div[data-testid="stDataFrame"]{border:1px solid #203348;border-radius:10px;overflow:hidden}
</style>''',unsafe_allow_html=True)

def weather(route):
    p=ROUTES[route]['points']; names=[]; rows=[]
    for name,lat,lon,elev in p:
        try:
            u='https://api.open-meteo.com/v1/forecast'
            r=requests.get(u,params={'latitude':lat,'longitude':lon,'current':'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m','timezone':'Asia/Karachi'},timeout=12)
            r.raise_for_status(); cur=r.json().get('current',{})
            rain=float(cur.get('precipitation') or 0); wind=float(cur.get('wind_gusts_10m') or cur.get('wind_speed_10m') or 0); code=int(cur.get('weather_code') or 0)
            score=min(100,int(rain*13+wind*1.1+(28 if code in [45,48,56,57,66,67,71,73,75,77,80,81,82,85,86,95,96,99] else 0)))
            tier='DANGEROUS' if score>=65 else 'WARNING' if score>=30 else 'NORMAL'
            rows.append({'Checkpoint':name,'Temp °C':cur.get('temperature_2m'),'Humidity %':cur.get('relative_humidity_2m'),'Rain mm':rain,'Wind km/h':cur.get('wind_speed_10m'),'Gust km/h':cur.get('wind_gusts_10m'),'Risk score':score,'Risk':tier,'Latitude':lat,'Longitude':lon})
        except Exception:
            rows.append({'Checkpoint':name,'Temp °C':None,'Humidity %':None,'Rain mm':None,'Wind km/h':None,'Gust km/h':None,'Risk score':None,'Risk':'DATA UNAVAILABLE','Latitude':lat,'Longitude':lon})
    return pd.DataFrame(rows)

def header(title,sub): st.markdown(f'<div class="hw-title">{title}</div><div class="hw-sub">{sub}</div>',unsafe_allow_html=True)
def pill(text): st.markdown(f'<span style="background:#12352e;color:#6ee7b7;padding:5px 10px;border-radius:20px;font-size:11px">{text}</span>',unsafe_allow_html=True)

with st.sidebar:
    logo=BASE / 'assets' / 'highway-watch-logo.png'
    if logo.exists(): st.image(str(logo), width=58)
    st.markdown('## 🛣️ Highway Watch')
    st.markdown('<span style="color:#34d399;font-size:12px">BALOCHISTAN COMMAND</span>',unsafe_allow_html=True)
    st.divider()
    page=st.radio('NAVIGATION',['Overview & Command','SOS & Welfare','Drivers & QR Pass','Map & Safe Havens','Alerts & Voice IVR','Road Status & Logs'],label_visibility='collapsed')
    st.divider()
    st.caption('ACTIVE HIGHWAY CORRIDOR')
    route=st.selectbox('Select corridor',list(ROUTES.keys()),label_visibility='collapsed')
    if st.button('↻ Sync Live Weather Feed',use_container_width=True): st.cache_data.clear(); st.rerun()
    st.divider(); st.caption('COMMAND DESK')
    operator=st.text_input('Operator name',value='Control Room Operator')
    st.caption('Weather feed: Open-Meteo · Road status: operator-entered')

now=datetime.now().strftime('%d %b %Y · %I:%M %p')
with st.container():
    a,b,c=st.columns([2.5,1.2,1])
    with a: st.markdown(f'**{page}**  \n<span class="hw-muted">{now} · {ROUTES[route]["code"]} · {ROUTES[route]["distance"]}</span>',unsafe_allow_html=True)
    with b: st.selectbox('Corridor',list(ROUTES.keys()),key='toproute',index=list(ROUTES).index(route),label_visibility='collapsed',on_change=lambda: st.session_state.update())
    with c:
        if st.button('🚨 Trigger SOS',type='primary',use_container_width=True): st.session_state['show_sos']=True
if 'toproute' in st.session_state and st.session_state.toproute!=route: route=st.session_state.toproute
if st.session_state.get('show_sos'):
    with st.form('quick_sos'):
        st.warning('Emergency incident entry. This records an incident locally; it does not contact emergency services.')
        sec=st.selectbox('Sector',[x[0] for x in ROUTES[route]['points']]); kind=st.selectbox('Emergency type',['Accident / Collision','Vehicle Breakdown','Medical Emergency','Stranded in Weather / Flood']); detail=st.text_area('Details')
        if st.form_submit_button('Record SOS'):
            code='SOS-'+datetime.now().strftime('%y%m%d%H%M%S'); conn.execute('INSERT INTO sos(code,driver,route,sector,kind,details,status,created) VALUES(?,?,?,?,?,?,?,?)',(code,'Not specified',route,sec,kind,detail,'ACTIVE SOS',now)); conn.commit(); st.session_state['show_sos']=False; st.success(f'{code} recorded in local incident log.'); st.rerun()

@st.cache_data(ttl=300,show_spinner=False)
def get_weather(r): return weather(r)

def load(table): return pd.read_sql_query(f'SELECT * FROM {table} ORDER BY id DESC',conn)

if page=='Overview & Command':
    header('Highway Operations Overview','Live weather intelligence, corridor risk and command desk')
    with st.spinner('Fetching checkpoint weather…'): df=get_weather(route)
    drivers=load('drivers'); alerts=load('alerts'); sos=load('sos'); roads=load('roads')
    danger=int((df.Risk=='DANGEROUS').sum()); warn=int((df.Risk=='WARNING').sum()); active=int((sos.status=='ACTIVE SOS').sum()) if not sos.empty else 0
    k=st.columns(4); k[0].metric('Registered Drivers',len(drivers)); k[1].metric('Danger Checkpoints',danger); k[2].metric('Warning Checkpoints',warn); k[3].metric('Active SOS',active)
    left,right=st.columns([1.6,1])
    with left:
        st.markdown('### Corridor Weather Intelligence')
        st.dataframe(df[['Checkpoint','Temp °C','Rain mm','Wind km/h','Risk score','Risk']],use_container_width=True,hide_index=True)
        st.caption('Weather data is fetched from Open-Meteo. Risk score is a simple indicative screening rule, not an official warning or validated prediction.')
    with right:
        st.markdown('### Corridor Summary'); st.markdown(f'<div class="hw-card"><div class="hw-muted">ROUTE</div><h3>{route}</h3><h2>{ROUTES[route]["distance"]}</h2><span class="hw-green">{ROUTES[route]["code"]}</span><hr><div class="hw-muted">CHECKPOINTS MONITORED</div><h2>{len(df)}</h2></div>',unsafe_allow_html=True)
        st.markdown('### Driver Safety Advisory')
        if danger: st.error('Potentially hazardous weather indicated. Avoid travel through affected areas until conditions are checked and authorities confirm the route is safe.')
        elif warn: st.warning('Weather conditions need caution. Recheck forecasts and official road updates before departure.')
        else: st.success('No elevated weather signal detected in the available feed. This does not confirm road safety.')
    st.markdown('### Route Checkpoints')
    st.map(df.rename(columns={'Latitude':'latitude','Longitude':'longitude'})[['latitude','longitude']].dropna(),zoom=5)
    st.markdown('### Recent Alerts & Road Updates')
    if not alerts.empty: st.dataframe(alerts.head(5),use_container_width=True,hide_index=True)
    else: st.info('No alerts have been recorded yet.')
elif page=='Drivers & QR Pass':
    header('Drivers & Vehicle Registry','Register drivers, assign highway corridors and track check-ins')
    with st.form('driver_form'):
        x,y,z=st.columns(3); name=x.text_input('Driver full name'); phone=y.text_input('Phone number'); vehicle=z.text_input('Vehicle description')
        x,y,z=st.columns(3); plate=x.text_input('Vehicle plate'); lang=y.selectbox('Alert language',LANGS); sector=z.selectbox('Current sector',[p[0] for p in ROUTES[route]['points']])
        if st.form_submit_button('＋ Register Driver'):
            if not name.strip() or not phone.strip(): st.error('Driver name and phone are required.')
            else:
                conn.execute('INSERT INTO drivers(name,phone,vehicle,plate,route,language,sector,created) VALUES(?,?,?,?,?,?,?,?)',(name,phone,vehicle,plate,route,lang,sector,now)); conn.commit(); st.success('Driver registered.'); st.rerun()
    data=load('drivers'); st.markdown('### Registered Drivers')
    if not data.empty: st.dataframe(data.drop(columns=['id']),use_container_width=True,hide_index=True)
    else: st.info('No drivers registered yet.')
elif page=='SOS & Welfare':
    header('SOS & Welfare Desk','Emergency incident queue and overdue-driver welfare tracking')
    with st.form('sos_form'):
        x,y=st.columns(2); driver=x.text_input('Driver name'); sector=y.selectbox('Incident sector',[p[0] for p in ROUTES[route]['points']]); kind=st.selectbox('Incident type',['Accident / Collision','Vehicle Breakdown','Medical Emergency','Stranded in Weather / Flood']); details=st.text_area('Incident details')
        if st.form_submit_button('Record Emergency Incident'):
            code='SOS-'+datetime.now().strftime('%y%m%d%H%M%S'); conn.execute('INSERT INTO sos(code,driver,route,sector,kind,details,status,created) VALUES(?,?,?,?,?,?,?,?)',(code,driver,route,sector,kind,details,'ACTIVE SOS',now)); conn.commit(); st.success(f'{code} saved locally.'); st.rerun()
    s=load('sos')
    if not s.empty:
        st.dataframe(s.drop(columns=['id']),use_container_width=True,hide_index=True)
        choices={f'{r.code} · {r.sector}':r.id for r in s.itertuples() if r.status=='ACTIVE SOS'}
        if choices:
            selected=st.selectbox('Resolve incident',list(choices))
            if st.button('Mark as Resolved'):
                conn.execute("UPDATE sos SET status='RESOLVED' WHERE id=?",(choices[selected],)); conn.commit(); st.rerun()
    else: st.info('No SOS incidents recorded.')
elif page=='Map & Safe Havens':
    header('Map & Safe Havens','Highway checkpoints and corridor reference points')
    pts=ROUTES[route]['points']; d=pd.DataFrame([{'Checkpoint':p[0],'latitude':p[1],'longitude':p[2],'Elevation':p[3]} for p in pts])
    st.map(d[['latitude','longitude']],zoom=5); st.dataframe(d,use_container_width=True,hide_index=True)
    st.markdown('### Alternate Corridor Reference'); st.markdown(f'<div class="hw-card"><b>{ROUTES[route]["alt"]}</b><p class="hw-muted">{ROUTES[route]["reason"]}</p></div>',unsafe_allow_html=True)
    st.warning('Map points and facility references are planning references. Verify locations, availability and route clearance with local authorities before relying on them.')
elif page=='Alerts & Voice IVR':
    header('Alerts & Voice IVR','Prepare multilingual safety messages and maintain an alert history')
    df=get_weather(route); risky=df[df.Risk.isin(['WARNING','DANGEROUS'])]
    severity=st.selectbox('Alert severity',['Advisory','Warning','Emergency']); language=st.selectbox('Language',LANGS); channel=st.selectbox('Channel',['SMS Gateway','Voice IVR','Checkpoint Display']); area=st.selectbox('Affected checkpoint',[p[0] for p in ROUTES[route]['points']])
    messages={'Urdu':f'موسمی صورتحال کے باعث {area} کے علاقے میں احتیاط کریں۔ سفر سے پہلے سرکاری روڈ اپ ڈیٹ چیک کریں۔ خطرناک صورتحال میں محفوظ مقام پر رکیں۔','English':f'Weather caution for {area}. Check official road updates before travel. Stop at a safe location if conditions become hazardous.','Pashto':f'د {area} په سیمه کې د هوا له امله احتیاط وکړئ. د سفر مخکې رسمي سړک معلومات وګورئ.','Balochi':f'{area}ءَ موسم ءِ بارواں احتیاط بکنت۔ سفر ءَ پێشتر سرکاری روڈ اپ ڈیٹ چیک کنّت.'}
    msg=st.text_area('Message preview',value=messages[language],height=120)
    st.caption('Voice and SMS are message previews only. No call or SMS is sent without a configured provider integration.')
    if st.button('Save Alert to History',type='primary'):
        conn.execute('INSERT INTO alerts(route,severity,language,message,channel,created) VALUES(?,?,?,?,?,?)',(route,severity,language,msg,channel,now)); conn.commit(); st.success('Alert saved to local history.'); st.rerun()
    if channel=='Voice IVR': st.info('Voice IVR preview: '+msg)
    st.markdown('### Weather Risk Context')
    if not risky.empty: st.dataframe(risky[['Checkpoint','Risk','Risk score']],use_container_width=True,hide_index=True)
    else: st.success('No warning-level weather signal in the current feed.')
    st.markdown('### Alert History'); a=load('alerts')
    if not a.empty: st.dataframe(a.drop(columns=['id']),use_container_width=True,hide_index=True)
    else: st.info('No saved alerts yet.')
elif page=='Road Status & Logs':
    header('Road Status & Logs','Operator-entered road condition records and clearance history')
    with st.form('road_form'):
        area=st.selectbox('Road section',[p[0] for p in ROUTES[route]['points']]); status=st.selectbox('Road status',['Open (Verified)','Restricted — Caution','Closed — Emergency','Clearance Pending']); note=st.text_area('Authority / field note')
        if st.form_submit_button('Save Road Status'):
            conn.execute('INSERT INTO roads(route,area,status,note,updated) VALUES(?,?,?,?,?)',(route,area,status,note,now)); conn.commit(); st.success('Road status saved.'); st.rerun()
    r=load('roads')
    if not r.empty: st.dataframe(r.drop(columns=['id']),use_container_width=True,hide_index=True)
    else: st.info('No road status records yet. Add a verified field update above.')

st.divider()
st.caption('Highway Watch · Balochistan | Weather feed: Open-Meteo | Road closures and emergency dispatch are not connected to official systems. Always follow verified authority instructions.')
