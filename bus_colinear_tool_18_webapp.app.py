import streamlit as st
import requests
import time
import json
import os
import csv
import io
import re
import matplotlib.pyplot as plt
from matplotlib import font_manager

# --- 1. 字体与基础配置 ---
@st.cache_resource
def get_custom_font():
    font_path = "simhei.ttf" 
    if os.path.exists(font_path):
        return font_manager.FontProperties(fname=font_path)
    return font_manager.FontProperties(family='sans-serif')

my_font = get_custom_font()

# --- 2. 北京地铁全线数据库 (保持不变) ---
SUBWAY_DB = {
    "1号线（八通线）": "福寿岭,苹果园,古城,八角游乐园,八宝山,玉泉路,五棵松,万寿路,公主坟,军事博物馆,木樨地,南礼士路,复兴门,西单,天安门西,天安门东,王府井,东单,建国门,永安里,国贸,大望路,四惠,四惠东,高碑店,传媒大学,双桥,管庄,八里桥,通州北苑,果园,九棵树,梨园,临河里,土桥,花庄,环球度假区",
    "2号线": "西直门,积水潭,鼓楼大街,安定门,雍和宫,东直门,东四十条,朝阳门,建国门,北京站,崇文门,前门,和平门,宣武门,长椿街,复兴门,阜成门,车公庄,西直门",
    "3号线": "东四十条,工人体育场,团结湖,朝阳公园,石佛营,朝阳站,姚家园,东坝南,东坝,东坝北",
    "4号线（大兴线）": "安河桥北,北宫门,西苑,圆明园,北京大学东门,中关村,海淀黄庄,人民大学,魏公村,国家图书馆,动物园,西直门,新街口,平安里,西四,灵境胡同,西单,宣武门,菜市口,陶然亭,北京南站,马家堡,角门西,公益西桥,新宫,西红门,高米店北,高米店南,枣园,清源路,黄村西大街,黄村火车站,义和庄,生物医药基地,天宫院",
    "5号线": "宋家庄,刘家窑,蒲黄榆,天坛东门,磁器口,崇文门,东单,灯市口,东四,张自忠路,北新桥,雍和宫,和平里北街,和平西桥,惠新西街南口,惠新西街北口,大屯路东,北苑路北,立水桥南,立水桥,天通苑南,天通苑,天通苑北",
    "6号线": "金安桥,苹果园,杨庄,西黄村,廖公庄,田村,海淀五路居,慈寿寺,花园桥,白石桥南,二里沟,车公庄西,车公庄,平安里,北海北,南锣鼓巷,东四,朝阳门,东大桥,呼家楼,金台路,十里堡,青年路,褡裢坡,黄渠,常营,草房,物资学院路,通州北关,北运河西,北运河东,郝家府,东夏园,潞城",
    "7号线": "北京西站,湾子,达官营,广安门内,菜市口,虎坊桥,珠市口,桥湾,磁器口,广渠门内,广渠门外,双井,九龙山,大郊亭,百子湾,化工,南楼梓庄,欢乐谷景区,垡头,双合,焦化厂,黄厂,郎辛庄,黑庄户,万盛西,万盛东,群芳,高楼金,花庄,环球度假区",
    "8号线": "朱辛庄,育知路,平西府,回龙观东大街,霍营,育新,西小口,永泰庄,林萃桥,森林公园南门,奥林匹克公园,奥体中心,北土城,安华桥,安德里北街,鼓楼大街,什刹海,南锣鼓巷,中国美术馆,金鱼胡同,王府井,前门,珠市口,天桥,永定门外,木樨园,海户屯,大红门,大红门南,和义,东高地,火箭万源,五福堂,德茂,瀛海",
    "9号线": "郭公庄,丰台科技园,科怡路,丰台南路,丰台东大街,七里庄,六里桥,六里桥东,北京西站,军事博物馆,白堆子,白石桥南,国家图书馆",
    "10号线": "巴沟,苏州街,海淀黄庄,知春里,知春路,西土城,牡丹园,健德门,北土城,安贞门,惠新西街南口,芍药居,太阳宫,三元桥,亮马桥,农业展览馆,团结湖,呼家楼,金台夕照,国贸,双井,劲松,潘家园,十里河,分钟寺,成寿寺,宋家庄,石榴庄,大红门,角门东,角门西,草桥,纪家庙,首经贸,丰台站,泥洼,西局,六里桥,莲花桥,公主坟,西钓鱼台,慈寿寺,车道沟,长春桥,火器营,巴沟",
    "11号线": "模式口,金安桥,北辛安,新首钢",
    "12号线": "四季青桥,蓝靛厂,长春桥,苏州桥,人民大学,大钟寺,蓟门桥,北太平庄,马甸桥,安华桥,安贞桥,和平西桥,光熙门,西坝河,三元桥,将台西,高家园,驼房营,东坝西,东坝北",
    "13号线": "西直门,大钟寺,知春路,五道口,上地,清河站,西二旗,龙泽,回龙观,霍营,立水桥,北苑,望京西,芍药居,光熙门,柳芳,东直门",
    "14号线": "张郭庄,园博园,大瓦窑,郭庄子,大井,七里庄,西局,东管头,丽泽商务区,菜户营,西铁营,景风门,永定门外,景泰,蒲黄榆,方庄,十里河,北工大西门,平乐园,九龙山,大望路,金台路,朝阳公园,枣营,东风北桥,将台,高家园,阜通,望京南,望京东,望京,来广营,善各庄",
    "15号线": "俸伯,顺义,石门,南法信,后沙峪,花梨坎,国展,孙河,马泉营,崔各庄,望京东,望京,望京西,关庄,大屯路东,安立路,奥林匹克公园,北沙滩,六道口,清华东路西口",
    "16号线": "北安河,温阳路,稻香湖路,屯佃,永丰,永丰南,西北旺,马连洼,农大南路,西苑,万泉河桥,苏州街,苏州桥,万寿寺,国家图书馆,二里沟,甘家口,玉渊潭东门,木樨地,达官营,红莲南路,丽泽商务区,东管头,丰台站,丰台南路,富丰桥,丰台科技园,榆树庄,宛平城",
    "17号线": "未来科学城北,未来科学城,天通苑东,清河营,红军营,望京西,太阳宫,西坝河,左家庄,工人体育场,东大桥,永安里,广渠门外,潘家园西,十里河,周家庄,十八里店,北神树,次渠北,次渠,嘉会湖",
    "18号线(规划)": "马连洼,上地软件园,东北旺,龙泽西,回龙观西大街,文华路,回龙观东大街,霍营东,天通苑",
    "19号线": "新宫,新发地,草桥,景风门,牛街,太平桥,平安里,积水潭,北太平庄,牡丹园"
}

# --- 3. 核心工具函数 ---
def fetch_bus_lines(api_key, location):
    url = "https://restapi.amap.com/v3/place/around"
    params = {"key": api_key, "location": location, "types": "150700", "radius": "500", "output": "json"}
    try:
        response = requests.get(url, params=params, timeout=10)
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
    fig, ax = plt.subplots(figsize=(16, max(8, len(bus_list)*0.35)))
    ax.grid(axis='x', color='lightblue', linestyle=':', linewidth=1)
    for bus, start, length in gantt_data:
        y = bus_list.index(bus)
        ax.barh(y, length-1, left=start, height=0.4, color='#FF7F00', edgecolor='none')
        ax.text(start, y, f" {bus} ", color='white', ha='right', va='center', fontproperties=my_font, fontsize=9, bbox=dict(facecolor='#E62129', edgecolor='none', pad=1))
    ax.xaxis.set_label_position('top'); ax.xaxis.tick_top()
    ax.set_xticks(range(len(station_data)))
    ax.set_xticklabels([s['name'] for s in station_data], rotation=90, fontproperties=my_font, fontsize=11)
    ax.set_xlim(-0.5, len(station_data)-0.5); ax.invert_yaxis()
    for s in ['left','bottom','right']: ax.spines[s].set_visible(False)
    ax.set_yticks([]); ax.set_title("轨道交通与周边公交共线分析可视化", fontproperties=my_font, fontsize=20, pad=40)
    plt.tight_layout()
    return fig

# --- 4. Streamlit 界面主体 ---
st.set_page_config(page_title="公交共线分析工具 V2.1", layout="wide")
st.title("🚇 公交与轨道共线分析系统 V2.1")

st.sidebar.header("🛠️ 调研模式选择")
mode = st.sidebar.radio("选择分析对象：", ["既有全线分析", "既有区间", "规划线路(坐标)"], horizontal=True)

# 处理模式逻辑
is_coord_mode = False
if mode == "既有全线分析":
    selected_line = st.sidebar.selectbox("选择地铁线路", list(SUBWAY_DB.keys()))
    input_str = SUBWAY_DB[selected_line]
elif mode == "既有区间":
    input_str = st.sidebar.text_area("输入站点名称(逗号分隔)", "马连洼, 上地软件园, 东北旺")
else:
    st.sidebar.markdown("🔗 [高德坐标拾取工具](https://lbs.amap.com/tools/picker)")
    input_str = st.sidebar.text_area("输入“名称 坐标”(例如：嘻嘻站 116.27,40.03; 分号分隔)", "点位A 116.27,40.03; 点位B 116.30,40.04")
    is_coord_mode = True

api_key = st.sidebar.text_input("高德 API 密钥", type="password", value=st.secrets.get("AMAP_KEY", ""))

if st.sidebar.button("🚀 启动核心分析"):
    if not api_key:
        st.error("请输入 API 密钥")
    else:
        station_data = []
        prog = st.progress(0)
        status = st.empty()
        
        # 统一处理输入数据
        if is_coord_mode:
            raw_items = [i.strip() for i in input_str.replace("\n", "").split(";") if i.strip()]
        else:
            raw_items = [i.strip() for i in input_str.split(",") if i.strip()]

        for i, item in enumerate(raw_items):
            status.text(f"正在分析第 {i+1}/{len(raw_items)} 个点位...")
            if is_coord_mode:
                # 增强型坐标解析：支持 "站名 坐标" 或 "坐标"
                match = re.search(r"(\d+\.\d+,\d+\.\d+)", item)
                if match:
                    loc = match.group(1)
                    name_part = item.replace(loc, "").strip()
                    name = f"{name_part}\n({loc})" if name_part else f"点位{i+1}\n({loc})"
                else:
                    loc, name = None, f"格式错误:{item}"
            else:
                name = item
                url = f"https://restapi.amap.com/v3/place/text?key={api_key}&keywords={name}地铁站&city=北京&types=150500&output=json"
                try:
                    res = requests.get(url, timeout=10).json()
                    loc = res["pois"][0]["location"] if res.get("pois") else None
                except: loc = None
            
            buses = fetch_bus_lines(api_key, loc) if loc else []
            station_data.append({"id": i, "name": name, "bus_list": buses})
            time.sleep(0.3)
            prog.progress((i+1)/len(raw_items))

        status.success("分析完成！")
        report = analyze_colinear(station_data)
        fig = draw_gantt(station_data, report)
        if fig:
            st.pyplot(fig)
            output = io.StringIO(); writer = csv.writer(output)
            writer.writerow(["起始站", "终点站", "站数", "公交线路"])
            for sid, recs in report.items():
                for l, s, e, b in recs:
                    writer.writerow([station_data[s]['name'].split('\n')[0], station_data[e]['name'].split('\n')[0], l, b])
            st.download_button("📥 导出分析明细 (CSV)", output.getvalue().encode('utf_8_sig'), "report.csv", "text/csv")

# --- 5. 网页使用说明书 (左下方) ---
st.sidebar.markdown("---")
with st.sidebar.expander("📖 网页使用说明书"):
    st.markdown("""
    **1. 既有全线分析**
    - 直接从下拉菜单选择北京既有地铁线路。
    - 系统自动加载该线路2026年最新站点序列。

    **2. 既有区间**
    - 手动输入站点名称，用**逗号**隔开。
    - 适用于跨线或特定路段调研。

    **3. 规划线路(坐标)**
    - 点击上方链接进入高德拾取器。
    - 格式：`站名 经度,纬度;`。
    - 示例：`嘻嘻站 116.27,40.03; 哈哈站 116.30,40.04`。
    - 必须用**分号**分隔不同点位。

    **4. 结果导出**
    - 运行结束后可下载CSV表格进行二次计算。
    """)
