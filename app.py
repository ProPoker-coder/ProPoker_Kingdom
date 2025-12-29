import streamlit as st
import pandas as pd
import sqlite3
import random
import re
import time
import io
import os
import base64
from datetime import datetime, timedelta

# --- 0. 系統核心配置 (Safari 穩定化優先) ---
st.set_page_config(
    page_title="PRO POKER 撲洛王國", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. 旗艦視覺系統物理焊接 (100% 全量展開) ---
def init_flagship_ui():
    conn = sqlite3.connect('poker_data.db')
    c = conn.cursor()
    m_spd = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_speed'").fetchone() or ("35",))[0]
    m_bg = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'welcome_bg_url'").fetchone() or ("https://img.freepik.com/free-photo/poker-table-dark-atmosphere_23-2151003784.jpg",))[0]
    m_txt = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_text'").fetchone() or ("撲洛王國營運中，歡迎回歸領地！",))[0]
    conn.close()
    
    st.markdown(f"""
        <style>
            /* 🌌 全環境底色強制鎖死 (防止 iOS Safari 變白) */
            html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {{
                background-color: #000000 !important;
                color: #FFFFFF !important;
            }}
            .main {{ background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Arial Black', sans-serif; }}
            
            /* 🎯 左上角開啟側邊欄箭頭高亮強化 */
            [data-testid="stSidebarCollapsedControl"] svg {{
                fill: #00FF00 !important;
                width: 45px !important;
                height: 45px !important;
                filter: drop-shadow(0px 0px 10px #00FF00);
            }}
            [data-testid="stSidebarCollapsedControl"] {{
                background-color: rgba(0, 255, 0, 0.1) !important;
                border-radius: 50% !important;
                padding: 5px !important;
            }}
            
            /* 🎨 分頁標籤 (Tabs) 高辨識度視覺強化 */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 12px;
                background-color: #111;
                padding: 12px;
                border-radius: 18px;
                border: 1px solid #333;
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 52px;
                background-color: #222;
                border-radius: 12px;
                color: #FFFFFF !important;
                font-weight: 900;
                border: 1px solid #444;
                font-size: 1.1em;
            }}
            .stTabs [aria-selected="true"] {{
                background-color: #FFD700 !important;
                color: #000000 !important;
                border: 2px solid #FFFFFF !important;
                transform: scale(1.05);
            }}

            /* 🏰 歡迎牆美工鎖死 */
            .welcome-wall {{ 
                text-align: center; padding: 45px 15px; 
                background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url('{m_bg}'); 
                background-size: cover; background-position: center; border-radius: 30px; border: 2px solid #FFD700; margin-top: 10px; 
            }}
            .welcome-title {{ font-size: clamp(2.3em, 7.5vw, 4.8em); color: #FFD700; font-weight: 900; text-shadow: 0 0 25px rgba(255,215,0,0.6); }}
            .welcome-subtitle {{ color: #FFFFFF; font-size: 1.4em; letter-spacing: 5px; margin-bottom: 25px; }}
            
            .feature-box {{ 
                background: rgba(20,20,20,0.95); 
                padding: 22px; 
                border-radius: 15px; 
                margin: 15px auto; 
                border: 1px solid #FFD700; 
                max-width: 580px; 
                text-align: left;
                box-shadow: 0 6px 20px rgba(0,0,0,0.8);
            }}
            .feature-title {{ color: #FFD700 !important; font-size: 1.25em !important; font-weight: 900 !important; text-shadow: 1px 1px 3px #000; display: block; }}
            .feature-desc {{ color: #FFFFFF !important; font-size: 1.1em !important; font-weight: 500 !important; line-height: 1.5; text-shadow: 1px 1px 2px #000; display: block; }}
            
            [data-testid="stSidebarNav"] {{ color: #00FF00 !important; }}
            
            .rank-card {{ padding: 25px 15px; border-radius: 25px; text-align: center; margin-bottom: 25px; border: 5px solid #FFD700; background-color: #111111; background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://img.freepik.com/free-vector/dark-carbon-fiber-texture-background_1017-33831.jpg'); background-size: cover; box-shadow: 0 0 40px rgba(255, 215, 0, 0.25); }}
            .xp-main {{ font-size: clamp(2.4em, 9vw, 4.2em); font-weight: 900; color: #FFFFFF; margin: 0; line-height: 1.1; }}
            .xp-sub {{ font-size: 1.7em; color: #FF4646; font-weight: bold; margin-top: 5px; }}
            
            .glory-title {{ color: #FFD700; font-size: 2.2em; font-weight: bold; text-align: center; margin-bottom: 20px; border-bottom: 4px solid #FFD700; padding-bottom: 10px; text-shadow: 0 0 15px rgba(255, 215, 0, 0.5); }}
            
            [data-testid="stTable"] {{ background-color: #1a1a1a !important; border-radius: 12px; padding: 10px; border: 1px solid #333; }}
            [data-testid="stTable"] td {{ color: #FFFFFF !important; font-weight: bold !important; text-shadow: 1px 1px 2px #000; padding: 15px !important; }}
            [data-testid="stTable"] th {{ color: #FFD700 !important; background-color: #262626 !important; padding: 12px !important; }}

            /* 🏅 月榜三甲特效物理焊接 */
            .gold-medal {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000 !important; padding: 18px; border-radius: 15px; font-weight: 900; text-align: center; margin-bottom: 12px; box-shadow: 0 0 20px rgba(255,215,0,0.8); border: 2px solid #FFF; }}
            .silver-medal {{ background: linear-gradient(45deg, #C0C0C0, #E8E8E8); color: #000 !important; padding: 16px; border-radius: 15px; font-weight: 900; text-align: center; margin-bottom: 12px; box-shadow: 0 0 15px rgba(192,192,192,0.6); border: 2px solid #FFF; }}
            .bronze-medal {{ background: linear-gradient(45deg, #CD7F32, #A0522D); color: #FFF !important; padding: 14px; border-radius: 15px; font-weight: 900; text-align: center; margin-bottom: 12px; box-shadow: 0 0 12px rgba(205,127,50,0.5); border: 2px solid #FFF; }}
            
            .marquee-container {{ background: #1a1a1a; color: #FFD700; padding: 12px 0; overflow: hidden; white-space: nowrap; border-top: 2px solid #FFD700; border-bottom: 2px solid #FFD700; margin-bottom: 25px; }}
            .marquee-text {{ display: inline-block; padding-left: 100%; animation: marquee {m_spd}s linear infinite; font-size: 1.5em; font-weight: bold; }}
            @keyframes marquee {{ 0% {{ transform: translate(0, 0); }} 100% {{ transform: translate(-100%, 0); }} }}
            
            .stButton>button {{ border-radius: 12px; border: 2px solid #c89b3c; color: #c89b3c; background: transparent; font-weight: bold; height: 50px; font-size: 1.1em; }}
            .stButton>button:hover {{ background: #c89b3c !important; color: #000 !important; }}
        </style>
        <div class="marquee-container"><div class="marquee-text">{m_txt}</div></div>
    """, unsafe_allow_html=True)

# --- 2. 資料庫核心 ---
def init_db():
    conn = sqlite3.connect('poker_data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS Members (pf_id TEXT PRIMARY KEY, name TEXT, xp REAL DEFAULT 0, xp_temp REAL DEFAULT 0, role TEXT DEFAULT "玩家", last_checkin TEXT, phone TEXT, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS Inventory (item_name TEXT PRIMARY KEY, stock INTEGER DEFAULT 0, item_value INTEGER DEFAULT 0, weight REAL DEFAULT 10.0, img_url TEXT, min_xp INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS Prizes (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, prize_name TEXT, status TEXT DEFAULT "待兌換", time DATETIME)')
    c.execute('CREATE TABLE IF NOT EXISTS Leaderboard (player_id TEXT PRIMARY KEY, hero_points INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS Monthly_God (player_id TEXT PRIMARY KEY, monthly_points INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS Import_History (filename TEXT PRIMARY KEY, import_time DATETIME)')
    c.execute('CREATE TABLE IF NOT EXISTS System_Settings (config_key TEXT PRIMARY KEY, config_value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS Staff_Logs (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id TEXT, player_id TEXT, prize_name TEXT, time DATETIME)')
    c.execute("INSERT OR IGNORE INTO System_Settings (config_key, config_value) VALUES ('reg_invite_code', '888')")
    c.execute("INSERT OR IGNORE INTO System_Settings (config_key, config_value) VALUES ('monthly_active', 'ON')")
    c.execute("INSERT OR IGNORE INTO Members (pf_id, name, role, xp, password) VALUES ('330999', '老闆', '老闆', 999999, 'kenken520')")
    c.execute("UPDATE Members SET password = 'kenken520', role = '老闆' WHERE pf_id = '330999'")
    conn.commit(); conn.close()

def get_rank_v2500(pts):
    if pts >= 2501: return "🏆 菁英 (Challenger)"
    elif pts >= 1001: return "🎖️ 大師 (Master)"
    elif pts >= 401:  return "💎 鑽石 (Diamond)"
    elif pts >= 151:  return "⬜ 白金 (Platinum)"
    else: return "🥈 白銀 (Silver)"

init_db(); init_flagship_ui()

# --- 3. 身份永續鎖定 (Safari 物理兼容版) ---
if "player_id" not in st.session_state:
    st.session_state.player_id = None
    st.session_state.access_level = "玩家"

try:
    current_params = st.query_params
    if "token" in current_params and st.session_state.player_id is None:
        token_id = str(current_params["token"]).strip()
        conn = sqlite3.connect('poker_data.db')
        u_auto = conn.execute("SELECT role FROM Members WHERE pf_id = ?", (token_id,)).fetchone()
        conn.close()
        if u_auto:
            st.session_state.player_id = token_id
            st.session_state.access_level = u_auto[0]
except:
    pass

with st.sidebar:
    st.title("🛡️ 認證總部")
    p_id_input = st.text_input("POKERFANS ID", value=st.session_state.player_id if st.session_state.player_id else "")
    conn = sqlite3.connect('poker_data.db')
    u_chk = conn.execute("SELECT role, password FROM Members WHERE pf_id = ?", (p_id_input,)).fetchone()
    invite_cfg = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'reg_invite_code'").fetchone() or ("888",))[0]
    conn.close()
    
    if p_id_input and u_chk:
        if st.text_input("密碼", type="password", key="login_pw") == u_chk[1]:
            if st.button("🚀 啟動領地系統"): 
                st.session_state.player_id = p_id_input
                st.session_state.access_level = u_chk[0]
                st.query_params["token"] = p_id_input
                st.rerun()
    elif p_id_input:
        with st.form("reg"):
            rn, rpw, ri = st.text_input("暱稱"), st.text_input("密碼", type="password"), st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                cr = sqlite3.connect('poker_data.db'); cr.execute("INSERT INTO Members (pf_id, name, role, xp, password) VALUES (?,?,?,?,?)", (p_id_input, rn, "玩家", 0, rpw)); cr.commit(); cr.close(); st.success("註冊成功！")
    
    if st.button("🚪 退出王國"): 
        st.session_state.player_id = None
        st.query_params.clear() 
        st.rerun()

if not st.session_state.player_id:
    st.markdown(f"""
        <div class="welcome-wall">
            <div class="welcome-title">PRO POKER</div>
            <div class="welcome-subtitle">撲 洛 傳 奇 殿 堂</div>
            <div class="feature-box">
                <span class="feature-title">🧧 玩家認證通道</span>
                <span class="feature-desc">輸入 POKERFANS ID 通過邀請碼驗證即可加入撲克殿堂。</span>
            </div>
            <div class="feature-box">
                <span class="feature-title">🎰 幸運轉盤抽抽樂</span>
                <span class="feature-desc">打牌賺XP簽到領紅利 大獎爆不完</span>
            </div>
            <div class="feature-box">
                <span class="feature-title">🛡️ 菁英榜單</span>
                <span class="feature-desc">尊榮排行彰顯不凡身價 提升段位可增加抽獎幸運值</span>
            </div>
            <p style="margin-top:40px; color:#FFFFFF; font-weight:bold; text-shadow:1px 1px 2px #000;">請點擊左上角螢光綠箭頭 ⬅️ 開啟認證面板</p>
        </div>
    """, unsafe_allow_html=True); st.stop()

# --- 4. 玩家主介面 ---
conn = sqlite3.connect('poker_data.db')
curr_m = datetime.now().strftime("%m")
t_p = st.tabs(["🪪 玩家排位", "🎰 轉盤抽獎", "⚔️ 軍火清冊", "🏆 榮耀榜"])

with t_p[0]:
    u_row = pd.read_sql_query("SELECT * FROM Members WHERE pf_id=?", conn, params=(st.session_state.player_id,)).iloc[0]
    h_pts = (conn.execute("SELECT hero_points FROM Leaderboard WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    m_pts = (conn.execute("SELECT monthly_points FROM Monthly_God WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    h_rk = conn.execute("SELECT COUNT(*) + 1 FROM Leaderboard WHERE hero_points > ?", (h_pts,)).fetchone()[0]
    st.markdown(f'''<div class="rank-card">
        <p style="color:#FFD700; margin:0;">永久 XP 餘額</p>
        <p class="xp-main">{u_row['xp']:,.0f}</p>
        <p class="xp-sub">紅利: {u_row['xp_temp']:,.0f}</p>
        <div class="stats-box"><div>🏆 英雄積分: {h_pts:,} (排名:{h_rk})</div><div>🔥 本月戰力: {m_pts:,}</div></div>
        <p style="color:gold; font-size:1.8em; margin-top:20px;">{get_rank_v2500(h_pts)}</p>
    </div>''', unsafe_allow_html=True)
    if st.button("🎰 幸運簽到"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        if u_row['last_checkin'] == today_str: st.warning("⚠️ 今日已完成簽到！")
        else:
            conn.execute("UPDATE Members SET xp_temp = xp_temp + 10, last_checkin = ? WHERE pf_id = ?", (today_str, st.session_state.player_id))
            conn.commit(); st.success("✅ 簽到成功！紅利 XP +10"); time.sleep(1); st.rerun()

    st.write("---"); st.markdown("#### 🎫 我的獲獎序號 (請至櫃台兌換)"); myp = pd.read_sql_query("SELECT id, prize_name, status FROM Prizes WHERE player_id=? ORDER BY id DESC", conn, params=(st.session_state.player_id,))
    for _, r in myp.iterrows():
        ca, cb = st.columns([4, 1])
        with ca: st.write(f"序號: {r['id']} | **{r['prize_name']}** | {r['status']}")
        with cb:
            if r['status'] == "已核銷" and st.button("🗑️", key=f"d_m_{r['id']}"):
                conn.execute("DELETE FROM Prizes WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

with t_p[1]:
    st.subheader("🎰 英雄幸運轉盤 (消耗 100 XP)")
    if st.button("🚀 啟動命運齒輪"):
        if (u_row['xp'] + u_row['xp_temp']) >= 100:
            inv = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0", conn)
            if not inv.empty:
                pb = st.progress(0)
                for i in range(100):
                    time.sleep(0.01); pb.progress(i + 1)
                win = random.choices(inv.to_dict('records'), weights=[float(w) for w in inv['weight'].tolist()], k=1)[0]
                if u_row['xp_temp'] >= 100: conn.execute("UPDATE Members SET xp_temp = xp_temp - 100 WHERE pf_id = ?", (st.session_state.player_id,))
                else: conn.execute("UPDATE Members SET xp_temp = 0, xp = xp - ? WHERE pf_id = ?", (100 - u_row['xp_temp'], st.session_state.player_id))
                conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (win['item_name'],))
                conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time) VALUES (?, ?, '待兌換', ?)", (st.session_state.player_id, win['item_name'], datetime.now()))
                conn.commit(); st.balloons(); st.success(f"🎰 獲得獎項：{win['item_name']}")
        else: st.warning("XP 不足")

with t_p[2]:
    st.subheader("⚔️ 撲洛殿堂：物資清冊展示")
    gun_df = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0 ORDER BY item_value DESC", conn)
    cols = st.columns(3)
    for idx, row in gun_df.iterrows():
        with cols[idx % 3]:
            img_src = row['img_url'] if row['img_url'] and row['img_url'].startswith('http') else "https://img.freepik.com/free-vector/modern-poker-chips-background_23-2147883740.jpg"
            st.markdown(f'''<div style="background:#111; border:1px solid #444; border-radius:15px; padding:10px; text-align:center;">
                <img src="{img_src}" style="width:100%; border-radius:10px; height:150px; object-fit:contain; background:#000;">
                <p style="color:#FFD700; font-weight:bold; margin-top:10px; font-size:1.1em;">{row['item_name']}</p>
                <p style="color:#FFF;">價值: {row['item_value']:,} XP</p>
                <p style="color:#666; font-size:0.8em;">庫存: {row['stock']}</p>
            </div>''', unsafe_allow_html=True)

with t_p[3]: # --- 【核心修復】：三甲特效對位 ---
    rk1, rk2 = st.columns(2)
    with rk1:
        st.markdown('<div class="glory-title">🎖️ 菁英總榜</div>', unsafe_allow_html=True)
        ldf = pd.read_sql_query("SELECT player_id as ID, hero_points FROM Leaderboard WHERE ID != '330999' ORDER BY hero_points DESC LIMIT 20", conn)
        if ldf.empty: st.info("🛡️ 王國傳奇尚未誕生...")
        else:
            ldf['榮耀牌位'] = ldf['hero_points'].apply(get_rank_v2500)
            st.table(ldf[['ID', '榮耀牌位']])
    with rk2:
        st.markdown(f'<div class="glory-title">🔥 {curr_m}月 巔峰戰力榜</div>', unsafe_allow_html=True)
        m_active = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]
        if m_active == "OFF": st.info("🏆 本月活動暫未開啟！")
        else:
            gdf = pd.read_sql_query("SELECT player_id as ID, monthly_points as 積分 FROM Monthly_God WHERE ID != '330999' ORDER BY 積分 DESC LIMIT 15", conn)
            if gdf.empty: st.warning("⚔️ 目前尚未有人上榜！")
            else:
                for i, r in gdf.iterrows():
                    # 物理對位：前三名各自顯示專屬特效
                    if i == 0: st.markdown(f'<div class="gold-medal">👑 冠軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 1: st.markdown(f'<div class="silver-medal">🥈 亞軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 2: st.markdown(f'<div class="bronze-medal">🥉 季軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    else: st.markdown(f'<div style="color:white; font-weight:bold; text-shadow:1px 1px 2px #000; margin-bottom:5px;">NO.{i+1}: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)

# --- 5. 指揮部 ---
if st.session_state.access_level in ["老闆", "店長"]:
    st.write("---"); st.header("⚙️ 王國指揮部")
    mt = st.tabs(["📁 精算", "📦 物資", "🚀 空投", "📢 視覺", "🎯 任命", "🗑️ 結算", "📜 核銷", "💾 備份"])

    with mt[0]:
        up = st.file_uploader("上傳報表 (CSV)", type="csv")
        if up and st.button("🚀 執行精算"):
            df_c = pd.read_csv(up); df_c.columns = df_c.columns.str.strip(); conn_c = sqlite3.connect('poker_data.db')
            if conn_c.execute("SELECT 1 FROM Import_History WHERE filename = ?", (up.name,)).fetchone(): st.error("❌ 重複匯入")
            else:
                matrix = { 1200:(200,1.0,[10,5,3]), 3400:(400,1.5,[15,8,5]), 6600:(600,2.0,[20,10,6]), 11000:(1000,3.0,[30,15,9]), 21500:(2000,5.0,[50,25,15]) }
                for _, rc in df_c.iterrows():
                    pid, nick = str(rc['ID']).strip(), str(rc['Nickname']).strip()
                    cash, re_e, rank, remark = float(rc['Cash Total']), int(rc['Re-entry']), int(rc['Rank']), str(rc['Remark'])
                    disc = sum(int(d) for d in re.findall(r'(\d+)折扣券', remark)); ents = re_e + 1
                    lv = min(matrix.keys(), key=lambda x:abs(x-((cash+disc)/ents)))
                    prof, base_p, r_l = matrix[lv]; xp_g = max(0, (prof * ents) - disc); pts_g = int((ents * base_p) + (r_l[rank-1] if rank <= 3 else 0))
                    conn_c.execute("INSERT OR IGNORE INTO Members (pf_id, name) VALUES (?,?)", (pid, nick))
                    conn_c.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (xp_g, pid))
                    conn_c.execute("INSERT OR IGNORE INTO Leaderboard (player_id) VALUES (?)", (pid,))
                    conn_c.execute("UPDATE Leaderboard SET hero_points = hero_points + ? WHERE player_id = ?", (pts_g, pid))
                    conn_c.execute("INSERT OR IGNORE INTO Monthly_God (player_id) VALUES (?)", (pid,))
                    conn_c.execute("UPDATE Monthly_God SET monthly_points = monthly_points + ? WHERE player_id = ?", (pts_g, pid))
                conn_c.execute("INSERT INTO Import_History VALUES (?,?)", (up.name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn_c.commit(); st.success("精算完成")
            conn_c.close()

    with mt[1]:
        with st.form("ni"):
            nn, nv, ns, nw = st.text_input("物資名"), st.number_input("價值", 0), st.number_input("庫存", 0), st.number_input("權重", 10.0)
            n_mx = st.number_input("XP 資格門檻", 0); img_url = st.text_input("圖片網址")
            if st.form_submit_button("🔨 上架"):
                conn.execute("INSERT OR REPLACE INTO Inventory (item_name, stock, item_value, weight, img_url, min_xp) VALUES (?,?,?,?,?,?)", (nn, ns, nv, nw, img_url, n_mx))
                conn.commit(); st.success("上架成功！"); st.rerun()
        st.write("---"); mdf = pd.read_sql_query("SELECT * FROM Inventory", conn)
        for _, ri in mdf.iterrows():
            with st.expander(f"📦 {ri['item_name']}"):
                eq, ew = st.number_input("補貨", 0, key=f"q_{ri['item_name']}"), st.number_input("權重", ri['weight'], key=f"w_{ri['item_name']}")
                new_url = st.text_input("連結", ri['img_url'], key=f"url_{ri['item_name']}")
                new_mx = st.number_input("門檻", int(ri['min_xp']), key=f"mx_{ri['item_name']}")
                if st.button("💾 更新", key=f"u_{ri['item_name']}"): 
                    conn.execute("UPDATE Inventory SET stock=stock+?, weight=?, img_url=?, min_xp=? WHERE item_name=?", (eq, ew, new_url, new_mx, ri['item_name'])); conn.commit(); st.rerun()

    with mt[2]:
        tid = st.text_input("目標玩家 ID"); val = st.number_input("XP 數額", 0)
        if st.button("🚀 執行空投"): conn.execute("UPDATE Members SET xp_temp = xp_temp + ? WHERE pf_id = ?", (val, tid)) if tid else conn.execute("UPDATE Members SET xp_temp = xp_temp + ?", (val,)); conn.commit(); st.success("成功")

    with mt[3]:
        ns_v = st.slider("速度", 5, 60, 35); ic_v = st.text_input("邀請碼", "888")
        txt_v = st.text_area("公告內容"); bg_v = st.text_input("背景 URL")
        curr_act = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]
        if st.button("🔓 開啟/🔒 關閉月榜"):
            new_act = "OFF" if curr_act == "ON" else "ON"
            conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('monthly_active', ?)", (new_act,))
            conn.commit(); st.rerun()
        if st.button("💾 保存設定"):
            conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('marquee_speed',?),('reg_invite_code',?),('marquee_text',?)", (str(ns_v), ic_v, txt_v))
            if bg_v: conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('welcome_bg_url',?)", (bg_v,))
            conn.commit(); st.rerun()

    with mt[4]:
        rid_v = st.text_input("調動 ID"); rl_v = st.selectbox("任命職位", ["玩家", "員工", "店長", "老闆"])
        if st.button("🪄 任命"):
            pws = {"老闆":"kenken520", "店長":"3939889", "員工":"88888", "玩家":"123456"}
            conn.execute("UPDATE Members SET role=?, password=? WHERE pf_id=?", (rl_v, pws[rl_v], rid_v)); conn.commit(); st.success("成功")

    with mt[5]:
        if st.session_state.access_level == "老闆":
            if st.button("⚖️ 規費削減"): conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 150)"); conn.commit(); st.success("完成")
            if st.button("🔥 粉碎月榜"): conn.execute("DELETE FROM Monthly_God"); conn.commit(); st.rerun()
            if st.button("💀 粉碎總榜"): conn.execute("DELETE FROM Leaderboard WHERE player_id != '330999'"); conn.commit(); st.rerun()

    with mt[6]: # 📜 核銷 (含自動入帳)
        sid_v = st.number_input("輸入序號 ID", value=0, step=1)
        if st.button("🔥 核銷銷帳", type="primary"):
            p_chk = conn.execute("SELECT player_id, prize_name, status FROM Prizes WHERE id=?", (sid_v,)).fetchone()
            if p_chk and p_chk[2] == '待兌換':
                prize_name, player_id = p_chk[1], p_chk[0]
                xp_match = re.search(r'(\d+)\s*(XP|點XP)', prize_name, re.IGNORECASE)
                conn.execute("UPDATE Prizes SET status='已核銷' WHERE id=?", (sid_v,))
                conn.execute("INSERT INTO Staff_Logs (staff_id, player_id, prize_name, time) VALUES (?,?,?,?)", (st.session_state.player_id, player_id, prize_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                auto_msg = ""
                if xp_match:
                    xp_val = int(xp_match.group(1))
                    conn.execute("UPDATE Members SET xp_temp = xp_temp + ? WHERE pf_id = ?", (xp_val, player_id))
                    auto_msg = f" 並且自動入帳 {xp_val} XP！"
                conn.commit(); st.success(f"✅ 核銷完成{auto_msg}"); time.sleep(1); st.rerun()
        ldf_v = pd.read_sql_query("SELECT id, staff_id, player_id, prize_name, time FROM Staff_Logs ORDER BY id DESC LIMIT 15", conn)
        for _, rv in ldf_v.iterrows():
            st.markdown(f'<div style="color:white; font-size:0.9em;">[{rv["time"]}] {rv["staff_id"]} 核銷 {rv["player_id"]} 的 {rv["prize_name"]}</div>', unsafe_allow_html=True)

    with mt[7]: # 💾 備份 (店長解放)
        if os.path.exists('poker_data.db'):
            with open('poker_data.db', 'rb') as f: st.download_button("📥 下載物理 DB", f, "Backup.db")
        if st.session_state.access_level == "老闆":
            rf = st.file_uploader("數據還原", type="db")
            if rf and st.button("🚨 強制物理還原"):
                with open('poker_data.db', 'wb') as f: f.write(rf.getbuffer())
                st.success("成功"); st.rerun()

conn.close()