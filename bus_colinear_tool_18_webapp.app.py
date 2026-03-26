import streamlit as st
import requests
import time
import json
import os
import operator
import csv
import io
import matplotlib.pyplot as plt
from matplotlib import font_manager

# --- 1. 云端环境字体适配 (核心改动) ---
@st.cache_resource
def load_custom_font():
    # Streamlit Cloud (Linux) 适配方案：使用系统内置的无衬线字体并支持中文渲染
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Liberation Sans', 'Ubuntu', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

load_custom_font()

# --- 2. 路径配置 (去掉绝对路径) ---
CACHE_FILE = "bus_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf8') as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, 'w', encoding='utf8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

# --- 3. 网络请求配置 (跳过代理) ---
session = requests.Session()
session.trust_env = False
session.proxies = {"http": None, "https": None}

def fetch_location(api_key, station_name):
    url = "https://restapi.amap.com/v3/place/text"
    params = {"key": api_key, "keywords": f"{station_name}地铁站", "city": "北京", "types": "150500", "output": "json"}
    try:
        response = session.get(url, params=params, timeout=10)
        return response.json()["pois"][0]["location"] if response.json().get("pois") else None
    except: return None

def fetch_bus_lines(api_key, location):
    url = "https://restapi.amap.com/v3/place/around"
    params = {"key": api_key, "location": location, "types": "150700", "radius": "500", "output": "json"}
    try:
        response = session.get(url, params=params, timeout=10)
        data = response.json()
        bus_lines = set()
        if data.get("status") == "1" and data.get("pois"):
            for poi in data["pois"]:
                address = poi.get("address", "")
                if address:
                    for line in address.replace(";", ",").split(","):
                        if line.strip(): bus_lines.add(line.strip())
        return list(bus_lines)
    except: return []

# --- 4. 绘图与分析逻辑 ---
def analyze_colinear(station_data):
    bus_routes = {}
    for item in station_data:
        for bus in item['bus_list']:
            if "停运" in bus: continue
            if bus not in bus_routes: bus_routes[bus] = []
            bus_routes[bus].append(item['id'])
    
    report = {i: [] for i in range(len(station_data))}
    for bus, stations in bus_routes.items():
        if not stations: continue
        segments = []
        cur = [stations[0]]
        for nxt in stations[1:]:
            if nxt == cur[-1] + 1: cur.append(nxt)
            else: segments.append(cur); cur = [nxt]
        segments.append(cur)
        for seg in segments:
            if len(seg) >= 2:
                report[seg[0]].append((len(seg), seg[0], seg[-1], bus))
    return report

def draw_gantt(station_data, report):
    gantt_data = []
    buses = set()
    for sid, recs in report.items():
        for l, s, e, b in recs:
            gantt_data.append((b, s, l))
            buses.add(b)
    if not buses: return None
    
    bus_list = sorted(list(buses))
    fig, ax = plt.subplots(figsize=(15, max(8, len(bus_list)*0.35)))
    ax.grid(axis='x', color='lightblue', linestyle=':', linewidth=1)
    
    for bus, start, length in gantt_data:
        y = bus_list.index(bus)
        ax.barh(y, length-1, left=start, height=0.3, color='#FF7F00')
        ax.text(start, y, f" {bus} ", color='white', ha='right', va='center', 
                bbox=dict(facecolor='#E62129', edgecolor='none', pad=1), weight='bold')

    ax.xaxis.set_label_position('top'); ax.xaxis.tick_top()
    ax.set_xticks(range(len(station_data)))
    ax.set_xticklabels([s['name'] for s in station_data], rotation=90, weight='bold')
    ax.set_xlim(-0.5, len(station_data)-0.5); ax.invert_yaxis()
    for s in ['left','bottom','right']: ax.spines[s].set_visible(False)
    ax.set_yticks([]); plt.tight_layout()
    return fig

# --- 5. Streamlit 界面 ---
st.title("🚇 公交与轨道共线智能分析系统")
st.sidebar.header("配置面板")
# 从云端安全设置读取或手动输入
api_key = st.sidebar.text_input("高德 API 密钥", type="password", value=st.secrets.get("AMAP_KEY", ""))
stations_raw = st.sidebar.text_area("站点列表(逗号分隔)", "马连洼, 上地软件园, 东北旺, 龙泽西, 回龙观西大街, 文华路, 回龙观东大街, 霍营东, 天通苑, 太平庄, 天通苑东")

if st.sidebar.button("启动分析"):
    if not api_key: st.error("请填入密钥")
    else:
        names = [n.strip() for n in stations_raw.split(",") if n.strip()]
        data = []; cache = load_cache()
        prog = st.progress(0); status = st.empty()
        
        for i, name in enumerate(names):
            status.text(f"正在处理: {name}")
            if name in cache:
                item = cache[name]; item['id'] = i; data.append(item)
            else:
                loc = fetch_location(api_key, name)
                buses = fetch_bus_lines(api_key, loc) if loc else []
                item = {"id": i, "name": name, "bus_list": buses}
                data.append(item); cache[name] = item; save_cache(cache)
                time.sleep(1)
            prog.progress((i+1)/len(names))
            
        status.text("分析完成！")
        rep = analyze_colinear(data)
        f = draw_gantt(data, rep)
        if f: st.pyplot(f)
        
        # 导出CSV
        out = io.StringIO(); w = csv.writer(out)
        w.writerow(["起点", "终点", "站数", "公交"])
        for sid, recs in rep.items():
            for l, s, e, b in recs:
                w.writerow([data[s]['name'], data[e]['name'], l, b])
        st.download_button("下载 CSV 数据", out.getvalue().encode('utf_8_sig'), "data.csv", "text/csv")