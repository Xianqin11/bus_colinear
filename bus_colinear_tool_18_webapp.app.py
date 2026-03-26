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

# --- 1. 云端环境字体加载逻辑 (精确匹配 simhei.ttf) ---
@st.cache_resource
def get_custom_font():
    # 这里的名字必须和你上传到 GitHub 的文件名完全一致
    font_path = "simhei.ttf" 
    if os.path.exists(font_path):
        return font_manager.FontProperties(fname=font_path)
    else:
        # 如果没找到文件，回退到系统默认，并在页面上给个提示
        return font_manager.FontProperties(family='sans-serif')

# 全局字体对象
my_font = get_custom_font()

# --- 2. 基础配置与路径 ---
CACHE_FILE = "bus_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf8') as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, 'w', encoding='utf8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

session = requests.Session()
session.trust_env = False
session.proxies = {"http": None, "https": None}

# --- 3. 高德 API 数据抓取逻辑 ---
def fetch_location(api_key, station_name):
    url = "https://restapi.amap.com/v3/place/text"
    params = {"key": api_key, "keywords": f"{station_name}地铁站", "city": "北京", "types": "150500", "output": "json"}
    try:
        response = session.get(url, params=params, timeout=10)
        data = response.json()
        return data["pois"][0]["location"] if data.get("pois") else None
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

# --- 4. 共线分析算法 ---
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

# --- 5. 绘图逻辑 (已集成黑体 simhei) ---
def draw_gantt(station_data, report):
    gantt_data = []
    buses = set()
    for sid, recs in report.items():
        for l, s, e, b in recs:
            gantt_data.append((b, s, l))
            buses.add(b)
    if not buses: return None
    
    bus_list = sorted(list(buses))
    fig, ax = plt.subplots(figsize=(16, max(8, len(bus_list)*0.35)))
    ax.grid(axis='x', color='lightblue', linestyle=':', linewidth=1)
    
    for bus, start, length in gantt_data:
        y = bus_list.index(bus)
        ax.barh(y, length-1, left=start, height=0.4, color='#FF7F00', edgecolor='none')
        # 应用自定义字体
        ax.text(start, y, f" {bus} ", color='white', ha='right', va='center', 
                fontproperties=my_font, fontsize=9,
                bbox=dict(facecolor='#E62129', edgecolor='none', pad=1))

    ax.xaxis.set_label_position('top')
    ax.xaxis.tick_top()
    ax.set_xticks(range(len(station_data)))
    # 应用自定义字体
    ax.set_xticklabels([s['name'] for s in station_data], rotation=90, fontproperties=my_font, fontsize=11)
    
    ax.set_xlim(-0.5, len(station_data)-0.5)
    ax.invert_yaxis()
    for s in ['left','bottom','right']: ax.spines[s].set_visible(False)
    ax.set_yticks([])
    
    # 应用自定义字体
    ax.set_title("轨道交通与周边公交共线分析可视化", fontproperties=my_font, fontsize=20, pad=40)
    
    plt.tight_layout()
    return fig

# --- 6. Streamlit 网页交互界面 ---
st.set_page_config(page_title="公交共线分析工具", layout="wide")
st.title("🚇 公交与轨道共线智能分析系统")

st.sidebar.header("🛠️ 配置面板")
default_key = st.secrets.get("AMAP_KEY", "")
api_key = st.sidebar.text_input("高德 API 密钥", type="password", value=default_key)

default_stations = "马连洼, 上地软件园, 东北旺, 龙泽西, 回龙观西大街, 文华路, 回龙观东大街, 霍营东, 天通苑, 太平庄, 天通苑东"
stations_raw = st.sidebar.text_area("站点列表 (逗号分隔)", default_stations, height=200)

if st.sidebar.button("启动核心分析"):
    if not api_key:
        st.error("请输入有效的高德 API 密钥！")
    else:
        names = [n.strip() for n in stations_raw.split(",") if n.strip()]
        station_data = []
        cache = load_cache()
        
        prog = st.progress(0)
        status = st.empty()
        
        for i, name in enumerate(names):
            status.text(f"正在分析站点: {name} ...")
            if name in cache and cache[name].get("bus_list"):
                item = cache[name]
                item['id'] = i
                station_data.append(item)
            else:
                loc = fetch_location(api_key, name)
                buses = fetch_bus_lines(api_key, loc) if loc else []
                item = {"id": i, "name": name, "bus_list": buses}
                station_data.append(item)
                if loc:
                    cache[name] = item
                    save_cache(cache)
                time.sleep(1)
            prog.progress((i+1)/len(names))
            
        status.success("数据采集与逻辑运算已完成！")
        
        colinear_rep = analyze_colinear(station_data)
        fig_output = draw_gantt(station_data, colinear_rep)
        
        if fig_output:
            st.pyplot(fig_output)
            output_csv = io.StringIO()
            writer = csv.writer(output_csv)
            writer.writerow(["起始站", "终点站", "共线站数", "公交线路"])
            for sid, records in colinear_rep.items():
                for length, s_id, e_id, bus in records:
                    writer.writerow([station_data[s_id]['name'], station_data[e_id]['name'], length, bus])
            
            st.download_button(
                label="📥 点击导出结构化明细数据 (CSV)",
                data=output_csv.getvalue().encode('utf_8_sig'),
                file_name="bus_colinear_report.csv",
                mime="text/csv"
            )
        else:
            st.info("在该搜索半径内未发现符合条件的共线公交线路。")
