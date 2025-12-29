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

# --- 0. 系統核心配置 (基於 v2500.34 穩定基座) ---
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
            
            /* 🎯 左上角開啟側邊欄箭頭高亮強化 (綠色雷射視覺) */
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
                font-size: 1.1em;
            }}
            .stTabs [aria-selected="true"] {{
                background-color: #FFD700 !important;
                color: #000000 !important;
                border: 2px solid #FFFFFF !important;
                transform: scale(1.03);
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
                background: rgba(20,20,20,0.95); padding: 22px; border-radius: 15px; margin: 15px auto; border: 1px solid #FFD700; max-width: 580px; text-align: left; box-shadow: 0 6px 20px rgba(0,0,0,0.8);
            }}
            .feature-title {{ color: #FFD700 !important; font-size: 1.25em !important; font-weight: 900 !important; text-shadow: 1px 1px 3px #000; display: block; }}
            .feature-desc {{ color: #FFFFFF !important; font-size: 1.1em !important; font-weight: 500 !important; line-height: 1.5; text-shadow: 1px 1px 2px #000; display: block; }}
            
            [data-testid="stSidebarNav"] {{ color: #00FF00 !important; }}
            
            /* 🪪 玩家排位卡美工 */
            .rank-card {{ padding: 25px 15px; border-radius: 25px; text-align: center; margin-bottom: 25px; border: 5px solid #FFD700; background-color: #111111; background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://img.freepik.com/free-vector/dark-carbon-fiber-texture-background_1017-33831.jpg'); background-size: cover; box-shadow: 0 0 40px rgba(255, 215, 0, 0.25); }}
            .xp-main {{ font-size: clamp(2.4em, 9vw, 4.2em); font-weight: 900; color: #FFFFFF; margin: 0; line-height: 1.1; }}
            .xp-sub {{ font-size: 1.7em; color: #FF4646; font-weight: bold; margin-top: 5px; }}
            
            /* 📊 排名資訊區美工 */
            .stats-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 20px; }}
            .stats-item {{ background: rgba(255,215,0,0.1); border: 1px solid #FFD700; padding: 10px 15px; border-radius: 12px; color: #FFFFFF; font-weight: bold; font-size: 1.1em; }}

            .glory-title {{ color: #FFD700; font-size: 2.2em; font-weight: bold; text-align: center; margin-bottom: 20px; border-bottom: 4px solid #FFD700; padding-bottom: 10px; text-shadow: 0 0 15px rgba(255, 215, 0, 0.5); }}
            
            [data-testid="stTable"] {{ background-color: #1a1a1a !important; border-radius: 12px; padding: 10px; border: 1px solid #333; }}
            [data-testid="stTable"] td {{ color: #FFFFFF !important; font-weight: bold !important; text-shadow: 1px 1px 2px #000; padding: 15px !important; }}
            [data-testid="stTable"] th {{ color: #FFD700 !important; background-color: #262626 !important; padding: 12px !important; }}

            /* 🏅 月榜金銀銅三甲特效 */
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
    c.execute('CREATE TABLE IF NOT EXISTS Inventory (item_name TEXT PRIMARY KEY, stock INTEGER DEFAULT 0, item_value INTEGER DEFAULT 0, weight REAL DEFAULT 10.0, img_url TEXT, min_xp INTEGER DEFAULT 0, status TEXT DEFAULT "上架中")')
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

# --- 【物理對位修正】：恢復純積分牌位判定 ---
def get_rank_v2500(pts):
    # 此處恢復為絕對積分門檻，即便排名第 1，分數不到也不會顯示菁英
    if pts >= 2501: return "🏆 菁英 (Challenger)"
    elif pts >= 1001: return "🎖️ 大師 (Master)"
    elif pts >= 401:  return "💎 鑽石 (Diamond)"
    elif pts >= 151:  return "⬜ 白金 (Platinum)"
    else: return "🥈 白銀 (Silver)"

init_db()
init_flagship_ui()

# --- 3. 身份辨識與穩定化 ---
if "player_id" not in st.session_state:
    st.session_state.player_id = None
    st.session_state.access_level = "玩家"

try:
    tk = st.query_params.get("token")
    if tk and st.session_state.player_id is None:
        conn = sqlite3.connect('poker_data.db')
        u = conn.execute("SELECT role FROM Members WHERE pf_id = ?", (str(tk),)).fetchone()
        conn.close()
        if u:
            st.session_state.player_id = tk
            st.session_state.access_level = u[0]
except:
    pass

with st.sidebar:
    st.title("🛡️ 認證總部")
    cur_id = st.session_state.player_id if st.session_state.player_id else ""
    p_id_input = st.text_input("POKERFANS ID", value=cur_id)
    conn = sqlite3.connect('poker_data.db')
    u_chk = conn.execute("SELECT role, password FROM Members WHERE pf_id = ?", (p_id_input,)).fetchone()
    invite_cfg = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'reg_invite_code'").fetchone() or ("888",))[0]
    conn.close()
    if p_id_input and u_chk:
        login_pw = st.text_input("密碼", type="password", key="sidebar_pw")
        if st.button("🚀 啟動領地系統"):
            if login_pw == u_chk[1]:
                st.session_state.player_id = p_id_input
                st.session_state.access_level = u_chk[0]
                st.query_params["token"] = p_id_input
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    elif p_id_input:
        with st.form("reg_sidebar"):
            rn = st.text_input("暱稱"); rpw = st.text_input("密碼", type="password"); ri = st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                cr = sqlite3.connect('poker_data.db'); cr.execute("INSERT INTO Members (pf_id, name, role, xp, password) VALUES (?,?,?,?,?)", (p_id_input, rn, "玩家", 0, rpw))
                cr.commit(); cr.close(); st.success("註冊成功！")
    if st.session_state.player_id:
        if st.button("🚪 退出王國"):
            st.session_state.player_id = None; st.query_params.clear(); st.rerun()

if not st.session_state.player_id:
    st.markdown(f"""
        <div class="welcome-wall">
            <div class="welcome-title">PRO POKER</div>
            <div class="welcome-subtitle">撲 洛 傳 奇 殿 堂</div>
            <div class="feature-box"><span class="feature-title">🧧 玩家認證通道</span><span class="feature-desc">輸入 POKERFANS ID 通過邀請碼驗證即可加入撲克殿堂。</span></div>
            <div class="feature-box"><span class="feature-title">🎰 幸運轉盤抽抽樂</span><span class="feature-desc">打牌賺XP簽到領紅利 大獎爆不完</span></div>
            <div class="feature-box"><span class="feature-title">🛡️ 菁英榜單</span><span class="feature-desc">尊榮排行彰顯不凡身價 提升段位可增加抽獎幸運值</span></div>
            <p style="margin-top:40px; color:#FFFFFF; font-weight:bold; text-shadow:1px 1px 2px #000;">請點擊左上角螢光綠箭頭 ⬅️ 開啟認證面板</p>
        </div>
    """, unsafe_allow_html=True); st.stop()

# --- 4. 玩家主介面 ---
conn = sqlite3.connect('poker_data.db')
curr_m = datetime.now().strftime("%m")
t_p = st.tabs(["🪪 玩家排位中心", "🎰 幸運轉盤", "⚔️ 撲洛軍火庫", "🏆 王國榮耀榜"])

with t_p[0]:
    u_row = pd.read_sql_query("SELECT * FROM Members WHERE pf_id=?", conn, params=(st.session_state.player_id,)).iloc[0]
    h_pts = (conn.execute("SELECT hero_points FROM Leaderboard WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    m_pts = (conn.execute("SELECT monthly_points FROM Monthly_God WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    m_active = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]

    # --- 【物理對位】：即時雙榜排名計算 ---
    e_rk_val = conn.execute("SELECT COUNT(*) + 1 FROM Leaderboard WHERE hero_points > ? AND player_id != '330999'", (h_pts,)).fetchone()[0]
    m_rk_val = conn.execute("SELECT COUNT(*) + 1 FROM Monthly_God WHERE monthly_points > ? AND player_id != '330999'", (m_pts,)).fetchone()[0]
    m_display_rk = f"第 {m_rk_val:,} 名" if m_active == "ON" else "比賽未開啟"

    st.markdown(f'''
    <div class="rank-card">
        <p style="color:#FFD700; margin:0;">永久 XP 餘額</p>
        <p class="xp-main">{u_row['xp']:,.0f}</p>
        <p class="xp-sub">紅利: {u_row['xp_temp']:,.0f}</p>
        <div class="stats-container">
            <div class="stats-item">🏆 英雄積分: {h_pts:,}</div>
            <div class="stats-item">🎖️ 菁英排名: 第 {e_rk_val:,} 名</div>
            <div class="stats-item">🔥 本月戰力: {m_pts:,}</div>
            <div class="stats-item">🏅 月榜排名: {m_display_rk}</div>
        </div>
        <p style="color:gold; font-size:1.8em; margin-top:20px;">{get_rank_v2500(h_pts)}</p>
    </div>
    ''', unsafe_allow_html=True)

    if st.button("🎰 幸運簽到"):
        today = datetime.now().strftime("%Y-%m-%d")
        if u_row['last_checkin'] == today: st.warning("⚠️ 今日已完成簽到！")
        else:
            conn.execute("UPDATE Members SET xp_temp = xp_temp + 10, last_checkin = ? WHERE pf_id = ?", (today, st.session_state.player_id))
            conn.commit(); st.success("✅ 簽到成功！紅利 XP +10"); time.sleep(1); st.rerun()
    with st.expander("🔐 安全中心：修改密碼"):
        new_pw = st.text_input("新密碼", type="password", key="reset_pw_box")
        if st.button("⚡ 執行鋼印替換") and new_pw:
            conn.execute("UPDATE Members SET password = ? WHERE pf_id = ?", (new_pw, st.session_state.player_id)); conn.commit(); st.success("✅ 修改成功！")
    st.write("---"); st.markdown("#### 🎫 我的中獎記錄"); myp = pd.read_sql_query("SELECT id, prize_name, status FROM Prizes WHERE player_id=? ORDER BY id DESC", conn, params=(st.session_state.player_id,))
    for _, r in myp.iterrows():
        ca, cb = st.columns([4, 1])
        with ca: st.write(f"序號: {r['id']} | **{r['prize_name']}** | {r['status']}")
        with cb:
            if r['status'] == "已核銷" and st.button("🗑️", key=f"d_m_{r['id']}"): conn.execute("DELETE FROM Prizes WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

with t_p[1]: # --- 【焊接】：轉盤穩定化 (基於 v2500.34) ---
    st.subheader("🎰 幸運轉盤 (消耗 100 XP)")
    if st.button("🚀 啟動命運齒輪"):
        if (u_row['xp'] + u_row['xp_temp']) >= 100:
            inv = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0 AND status = '上架中'", conn)
            if not inv.empty:
                pb = st.progress(0)
                for i in range(100): time.sleep(0.01); pb.progress(i + 1)
                win = random.choices(inv.to_dict('records'), weights=[float(w) for w in inv['weight'].tolist()], k=1)[0]
                if u_row['xp_temp'] >= 100: conn.execute("UPDATE Members SET xp_temp = xp_temp - 100 WHERE pf_id = ?", (st.session_state.player_id,))
                else: conn.execute("UPDATE Members SET xp_temp = 0, xp = xp - ? WHERE pf_id = ?", (100 - u_row['xp_temp'], st.session_state.player_id))
                conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (win['item_name'],))
                conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time) VALUES (?, ?, '待兌換', ?)", (st.session_state.player_id, win['item_name'], datetime.now()))
                conn.commit(); st.balloons(); st.success(f"🎰 獲得獎項：{win['item_name']}")
        else: st.warning("XP 不足")

with t_p[2]: # --- 【焊接】：老闆贈禮按鈕 ---
    st.subheader("⚔️ 撲洛軍火展示")
    gun_df = pd.read_sql_query("SELECT * FROM Inventory WHERE status = '上架中' ORDER BY item_value DESC", conn)
    cols = st.columns(3)
    for idx, row in gun_df.iterrows():
        with cols[idx % 3]:
            img_src = row['img_url'] if row['img_url'] and row['img_url'].startswith('http') else "https://img.freepik.com/free-vector/modern-poker-chips-background_23-2147883740.jpg"
            st.markdown(f'''<div style="background:#111; border:1px solid #444; border-radius:15px; padding:10px; text-align:center;">
                <img src="{img_src}" style="width:100%; border-radius:10px; height:150px; object-fit:contain; background:#000;">
                <p style="color:#FFD700; font-weight:bold; margin-top:10px;">{row['item_name']}</p><p style="color:#FFF;">價值: {row['item_value']:,} XP</p>
                <p style="color:#666;">庫存: {row['stock']}</p></div>''', unsafe_allow_html=True)
            if st.session_state.access_level == "老闆" and row['stock'] > 0:
                with st.expander(f"🎁 老闆贈送"):
                    gtid = st.text_input("玩家 ID", key=f"gf_{row['item_name']}")
                    if st.button("執行贈送", key=f"gb_{row['item_name']}") and gtid:
                        conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (row['item_name'],))
                        conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time) VALUES (?, ?, '待兌換', ?)", (gtid, row['item_name'], datetime.now()))
                        conn.commit(); st.success("已贈出"); st.rerun()

with t_p[3]:
    rk1, rk2 = st.columns(2)
    with rk1:
        st.markdown('<div class="glory-title">🎖️ 菁英總榜</div>', unsafe_allow_html=True)
        ldf = pd.read_sql_query("SELECT player_id as ID, hero_points FROM Leaderboard WHERE ID != '330999' ORDER BY hero_points DESC LIMIT 20", conn)
        if not ldf.empty:
            ldf['榮耀牌位'] = ldf['hero_points'].apply(get_rank_v2500)
            st.table(ldf[['ID', '榮耀牌位']])
    with rk2:
        st.markdown(f'<div class="glory-title">🔥 {curr_m}月 巔峰戰力榜</div>', unsafe_allow_html=True)
        if m_active == "OFF": st.info("🏆 本月活動暫未開啟！")
        else:
            gdf = pd.read_sql_query("SELECT player_id as ID, monthly_points as 積分 FROM Monthly_God WHERE ID != '330999' ORDER BY 積分 DESC LIMIT 15", conn)
            if not gdf.empty:
                for i, r in gdf.iterrows():
                    if i == 0: st.markdown(f'<div class="gold-medal">👑 冠軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 1: st.markdown(f'<div class="silver-medal">🥈 亞軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 2: st.markdown(f'<div class="bronze-medal">🥉 季軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    else: st.markdown(f'<div style="color:white; font-weight:bold; text-shadow:1px 1px 2px #000; margin-bottom:5px;">NO.{i+1}: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)

# --- 5. 指揮部 (10% XP、1200 權重、三方案規費焊接) ---
if st.session_state.access_level in ["老闆", "店長", "員工"]:
    st.write("---"); st.header("⚙️ 王國指揮部")
    user_role = st.session_state.access_level
    if user_role == "老闆": active_labels = ["📁 精算", "📦 物資", "🚀 空投", "📢 視覺", "🎯 任命", "🗑️ 結算", "📜 核銷", "💾 備份"]
    elif user_role == "店長": active_labels = ["📁 精算", "📜 核銷", "💾 備份"]
    elif user_role == "員工": active_labels = ["📜 核銷"]
    else: active_labels = []

    if active_labels:
        mt = st.tabs(active_labels)
        for i, label in enumerate(active_labels):
            with mt[i]:
                if label == "📁 精算": # --- 【核心對位】：10% 回饋與 1200 權重 0.75 ---
                    st.info("💡 檔名規範：2025_12_30_3400... (必須含日期與金額)")
                    up = st.file_uploader("上傳報表", type="csv")
                    if up:
                        fn = up.name
                        date_m = re.search(r'(\d{4}_\d{1,2}_\d{1,2})', fn)
                        amt_m = re.search(r'(1200|3400|6600|11000|21500)', fn)
                        if not date_m or not amt_m: st.error("❌ 檔名格式錯誤")
                        else:
                            buy_val = int(amt_m.group(1))
                            st.success(f"✅ 辨識成功：買入 {buy_val}")
                            if st.button("🚀 執行智能精算匯入"):
                                df_c = None
                                for enc in ['utf-8-sig', 'big5', 'gbk']:
                                    try:
                                        up.seek(0)
                                        df_c = pd.read_csv(up, encoding=enc, sep=None, engine='python')
                                        break
                                    except: continue
                                if df_c is not None:
                                    df_c.columns = df_c.columns.str.strip(); conn_c = sqlite3.connect('poker_data.db')
                                    if conn_c.execute("SELECT 1 FROM Import_History WHERE filename = ?", (fn,)).fetchone(): st.error("❌ 已匯入過")
                                    else:
                                        # 1200 權重 0.75，其餘維持 v2500.34
                                        matrix = { 1200:(200, 0.75, [10,5,3]), 3400:(400, 1.5, [15,8,5]), 6600:(600, 2.0,[20,10,6]), 11000:(1000, 3.0,[30,15,9]), 21500:(2000, 5.0,[50,25,15]) }
                                        prof_base, base_p, r_l = matrix[buy_val]
                                        for _, rc in df_c.iterrows():
                                            pid, nick = str(rc['ID']).strip(), str(rc['Nickname']).strip()
                                            rk = int(rc['Rank']); re_e = int(rc['Re-entry']); ents = re_e + 1
                                            rem = str(rc.get('Remark', ''))
                                            disc = sum(int(d) for d in re.findall(r'(\d+)折扣券', rem))
                                            # 行政費回饋物理校準為 10%
                                            xp_g = max(0, (prof_base * 0.1 * ents) - (disc * 0.1))
                                            pts_g = int((ents * base_p) + (r_l[rank-1] if rk <= 3 else 0))
                                            conn_c.execute("INSERT OR IGNORE INTO Members (pf_id, name) VALUES (?,?)", (pid, nick))
                                            conn_c.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (xp_g, pid))
                                            conn_c.execute("INSERT OR IGNORE INTO Leaderboard (player_id) VALUES (?)", (pid,))
                                            conn_c.execute("UPDATE Leaderboard SET hero_points = hero_points + ? WHERE player_id = ?", (pts_g, pid))
                                            conn_c.execute("INSERT OR IGNORE INTO Monthly_God (player_id) VALUES (?)", (pid,))
                                            conn_c.execute("UPDATE Monthly_God SET monthly_points = monthly_points + ? WHERE player_id = ?", (pts_g, pid))
                                        conn_c.execute("INSERT INTO Import_History VALUES (?, ?)", (fn, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                        conn_c.commit(); st.success("精算完成")
                                    conn_c.close()
                    st.write("---"); log_df = pd.read_sql_query("SELECT filename as 檔名, import_time as 時間 FROM Import_History ORDER BY 時間 DESC", conn)
                    if not log_df.empty:
                        st.table(log_df)
                        if user_role == "老闆":
                            if st.button("🗑️ 清空歷史紀錄"): conn.execute("DELETE FROM Import_History"); conn.commit(); st.rerun()

                elif label == "📦 物資":
                    with st.form("ni_form"):
                        nn = st.text_input("物資名"); nv = st.number_input("價值", 0); ns = st.number_input("庫存", 0); nw = st.number_input("權重", 10.0); nmx = st.number_input("XP 門檻", 0); img = st.text_input("網址")
                        if st.form_submit_button("🔨 執行上架"):
                            conn.execute("INSERT OR REPLACE INTO Inventory (item_name, stock, item_value, weight, img_url, min_xp, status) VALUES (?,?,?,?,?,?, '上架中')", (nn, ns, nv, nw, img, nmx)); conn.commit(); st.rerun()
                    st.write("---")
                    mdf = pd.read_sql_query("SELECT * FROM Inventory", conn)
                    for _, ri in mdf.iterrows():
                        with st.expander(f"📦 管理：{ri['item_name']} ({ri['status']})"):
                            eq = st.number_input("補貨", 0, key=f"q_{ri['item_name']}"); ew = st.number_input("修正權重", value=ri['weight'], key=f"w_{ri['item_name']}")
                            nx = st.number_input("門檻", value=int(ri['min_xp']), key=f"mx_{ri['item_name']}"); nu = st.text_input("網址", value=ri['img_url'], key=f"url_{ri['item_name']}")
                            estat = st.selectbox("狀態", ["上架中", "下架中"], index=0 if ri['status']=="上架中" else 1, key=f"st_{ri['item_name']}")
                            if st.button("💾 保存", key=f"s_{ri['item_name']}"): 
                                conn.execute("UPDATE Inventory SET stock=stock+?, weight=?, img_url=?, min_xp=?, status=? WHERE item_name=?", (eq, ew, nu, nx, estat, ri['item_name'])); conn.commit(); st.rerun()
                            if st.button("🗑️ 刪除", key=f"del_{ri['item_name']}"): conn.execute("DELETE FROM Inventory WHERE item_name=?", (ri['item_name'],)); conn.commit(); st.rerun()

                elif label == "🚀 空投":
                    st.subheader("🎯 階級精準空投")
                    drop_mode = st.selectbox("對象", ["單一玩家 ID", "全體玩家", "🏆 菁英階級", "🎖️ 大師階級", "💎 鑽石階級", "⬜ 白金階級", "🥈 白銀階級"])
                    target_ids = []
                    if drop_mode == "單一玩家 ID":
                        tid_in = st.text_input("輸入玩家 ID")
                        if tid_in: target_ids = [tid_in]
                    elif drop_mode == "全體玩家": target_ids = pd.read_sql_query("SELECT pf_id FROM Members", conn)['pf_id'].tolist()
                    else:
                        rank_map = {"🏆 菁英階級":"🏆 菁英", "🎖️ 大師階級":"🎖️ 大師", "💎 鑽石階級":"💎 鑽石", "⬜ 白金階級":"⬜ 白金", "🥈 白銀階級":"🥈 白銀"}
                        all_l = pd.read_sql_query("SELECT player_id, hero_points FROM Leaderboard", conn)
                        all_l['rk'] = all_l['hero_points'].apply(get_rank_v2500)
                        target_ids = all_l[all_l['rk'].str.contains(rank_map[drop_mode])]['player_id'].tolist()
                    dxp = st.number_input("永久 XP", 0); ditem = st.selectbox("贈禮", ["無"] + pd.read_sql_query("SELECT item_name FROM Inventory WHERE stock > 0", conn)['item_name'].tolist())
                    if st.button("🚀 執行"):
                        for tid in target_ids:
                            if dxp > 0: conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (dxp, tid))
                            if ditem != "無":
                                conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (ditem,))
                                conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time) VALUES (?, ?, '待兌換', ?)", (tid, ditem, datetime.now()))
                        conn.commit(); st.success("完成")

                elif label == "📢 視覺":
                    ns_v = st.slider("速度", 5, 60, 35); ic_v = st.text_input("邀請碼", "888"); txt_v = st.text_area("公告")
                    if st.button("💾 保存"):
                        conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_speed',?),('reg_invite_code',?),('marquee_text',?)", (str(ns_v), ic_v, txt_v)); conn.commit(); st.rerun()

                elif label == "🎯 任命":
                    rid_v = st.text_input("目標 ID"); rl_v = st.selectbox("職位", ["玩家", "員工", "店長", "老闆"])
                    if st.button("🪄 執行"):
                        pws = {"老闆":"kenken520", "店長":"3939889", "員工":"88888", "玩家":"123456"}
                        conn.execute("UPDATE Members SET role=?, password=? WHERE pf_id=?", (rl_v, pws[rl_v], rid_v)); conn.commit(); st.success("成功")

                elif label == "🗑️ 結算": # --- 【物理焊接】：方案 A/B/C 結算 ---
                    st.subheader("⚖️ 英雄規費削減方案選擇")
                    scheme = st.selectbox("削減策略", [
                        "方案 A：固定定額 (每人 -150)", 
                        "方案 B：階級權重 (菁英-200 / 大師-100 / 其餘-50)", 
                        "方案 C：比例削減 (全體 Pts 物理削減 -10%)"
                    ])
                    if st.button("🚨 執行結算"):
                        if "方案 A" in scheme: conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 150) WHERE player_id != '330999'")
                        elif "方案 B" in scheme:
                            conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 200) WHERE hero_points >= 2501 AND player_id != '330999'")
                            conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 100) WHERE hero_points BETWEEN 1001 AND 2500 AND player_id != '330999'")
                            conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 50) WHERE hero_points <= 1000 AND player_id != '330999'")
                        elif "方案 C" in scheme: conn.execute("UPDATE Leaderboard SET hero_points = CAST(hero_points * 0.9 AS INTEGER) WHERE player_id != '330999'")
                        conn.commit(); st.success(f"已按 {scheme} 成功結算！"); st.rerun()
                    st.write("---")
                    if st.button("🔥 粉碎月榜"): conn.execute("DELETE FROM Monthly_God"); conn.commit(); st.rerun()
                    if user_role == "老闆":
                        if st.button("💀 粉碎菁英總榜"): conn.execute("DELETE FROM Leaderboard WHERE player_id != '330999'"); conn.commit(); st.rerun()

                elif label == "📜 核銷":
                    sid_v = st.number_input("序號 ID", value=0, step=1)
                    if st.button("🔥 核銷銷帳", type="primary"):
                        p_chk = conn.execute("SELECT player_id, prize_name, status FROM Prizes WHERE id=?", (sid_v,)).fetchone()
                        if p_chk and p_chk[2] == '待兌換':
                            prize_name, player_id = p_chk[1], p_chk[0]
                            p_val = (conn.execute("SELECT item_value FROM Inventory WHERE item_name = ?", (prize_name,)).fetchone() or (0,))[0]
                            can_v = (user_role == "老闆") or (user_role == "店長" and p_val <= 11000) or (user_role == "員工" and p_val <= 3400)
                            if can_v:
                                xp_m = re.search(r'(\d+)\s*(XP|點XP)', prize_name, re.IGNORECASE)
                                conn.execute("UPDATE Prizes SET status='已核銷' WHERE id=?", (sid_v,))
                                conn.execute("INSERT INTO Staff_Logs (staff_id, player_id, prize_name, time) VALUES (?,?,?,?)", (st.session_state.player_id, player_id, prize_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                if xp_m: conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (int(xp_m.group(1)), player_id))
                                conn.commit(); st.success("✅ 核銷完成！"); time.sleep(1); st.rerun()
                            else: st.error("❌ 權限不足")
                    ldf_v = pd.read_sql_query("SELECT id, staff_id, player_id, prize_name, time FROM Staff_Logs ORDER BY id DESC LIMIT 15", conn)
                    for _, rv in ldf_v.iterrows(): st.markdown(f'<div style="color:white; font-size:0.8em;">[{rv["time"]}] {rv["staff_id"]} 核銷 {rv["player_id"]} 的 {rv["prize_name"]}</div>', unsafe_allow_html=True)

                elif label == "💾 備份":
                    if os.path.exists('poker_data.db'):
                        with open('poker_data.db', 'rb') as f: st.download_button("📥 下載 DB", f, "Backup.db")
                    if user_role == "老闆":
                        rf = st.file_uploader("還原", type="db")
                        if rf and st.button("🚨 強制物理還原"):
                            with open('poker_data.db', 'wb') as f: f.write(rf.getbuffer()); st.success("成功"); st.rerun()

conn.close()