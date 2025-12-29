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

# --- 0. 系統核心配置 ---
st.set_page_config(page_title="PRO POKER 黑金王國", page_icon="🃏", layout="wide")

# --- 1. 旗艦視覺系統物理焊接 (100% 全量展開) ---
def init_flagship_ui():
    conn = sqlite3.connect('poker_data.db')
    c = conn.cursor()
    m_spd = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_speed'").fetchone() or ("35",))[0]
    m_bg = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'welcome_bg_url'").fetchone() or ("https://img.freepik.com/free-photo/poker-table-dark-atmosphere_23-2151003784.jpg",))[0]
    m_txt = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_text'").fetchone() or ("黑金王國營運中，歡迎回歸領地！",))[0]
    conn.close()
    
    st.markdown(f"""
        <style>
            .main {{ background-color: #000000; color: #FFFFFF; font-family: 'Arial Black', sans-serif; }}
            /* 🏰 歡迎牆美工鎖死 */
            .welcome-wall {{ 
                text-align: center; padding: 60px 20px; 
                background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('{m_bg}'); 
                background-size: cover; background-position: center; border-radius: 30px; border: 2px solid #FFD700; margin-top: 20px; 
            }}
            .welcome-title {{ font-size: clamp(2.5em, 8vw, 5em); color: #FFD700; font-weight: 900; text-shadow: 0 0 30px rgba(255,215,0,0.6); }}
            .welcome-subtitle {{ color: #FFFFFF; font-size: 1.5em; letter-spacing: 5px; margin-bottom: 30px; }}
            .feature-box {{ background: rgba(255,215,0,0.1); padding: 20px; border-radius: 15px; margin: 10px auto; border: 1px solid #FFD700; max-width: 600px; text-align: left; }}
            
            /* 會員卡與 XP 數據卡美工焊死 */
            .rank-card {{ 
                padding: 30px 20px; border-radius: 30px; text-align: center; margin-bottom: 30px; border: 6px solid #FFD700; 
                background-color: #111111; 
                background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://img.freepik.com/free-vector/dark-carbon-fiber-texture-background_1017-33831.jpg'); 
                background-size: cover; box-shadow: 0 0 50px rgba(255, 215, 0, 0.2); 
            }}
            .xp-main {{ font-size: clamp(2.5em, 10vw, 4.5em); font-weight: 900; color: #FFFFFF; margin: 0; line-height: 1.1; }}
            .xp-sub {{ font-size: 1.8em; color: #FF4646; font-weight: bold; margin-top: 5px; }}
            .stats-box {{ font-size: 1.3em; color: #AAAAAA; margin-top: 15px; border-top: 1px solid #333; padding-top: 15px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px; }}
            
            /* 🏆 標題與排行榜特效焊死 */
            .glory-title {{ color: #FFD700; font-size: 2.2em; font-weight: bold; text-align: center; margin-bottom: 20px; border-bottom: 4px solid #FFD700; padding-bottom: 10px; text-shadow: 0 0 15px rgba(255, 215, 0, 0.5); }}
            .gold-medal {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000 !important; padding: 15px; border-radius: 15px; font-weight: 900; text-align: center; margin-bottom: 10px; box-shadow: 0 0 20px rgba(255,215,0,0.8); font-size: 1.4em; }}
            .silver-medal {{ background: linear-gradient(45deg, #C0C0C0, #E8E8E8); color: #000 !important; padding: 12px; border-radius: 12px; font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 1.2em; }}
            .bronze-medal {{ background: linear-gradient(45deg, #CD7F32, #A0522D); color: #FFF !important; padding: 10px; border-radius: 10px; font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 1.1em; }}
            
            .marquee-container {{ background: #1a1a1a; color: #FFD700; padding: 12px 0; overflow: hidden; white-space: nowrap; border-top: 2px solid #FFD700; border-bottom: 2px solid #FFD700; margin-bottom: 25px; }}
            .marquee-text {{ display: inline-block; padding-left: 100%; animation: marquee {m_spd}s linear infinite; font-size: 1.6em; font-weight: bold; }}
            @keyframes marquee {{ 0% {{ transform: translate(0, 0); }} 100% {{ transform: translate(-100%, 0); }} }}
            
            .stButton>button {{ border-radius: 12px; border: 2px solid #c89b3c; color: #c89b3c; background: transparent; font-weight: bold; transition: 0.3s; width: 100%; height: 50px; font-size: 1.2em; }}
            .stButton>button:hover {{ background: #c89b3c !important; color: #000 !important; }}
            .stTable td, .stTable th {{ font-size: 1.4em !important; color: #FFFFFF !important; }}
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

# --- 3. 認證系統 ---
if "player_id" not in st.session_state: st.session_state.player_id = None
if "access_level" not in st.session_state: st.session_state.access_level = "玩家"

with st.sidebar:
    st.title("🛡️ 認證總部")
    p_id = st.text_input("POKERFANS ID", value=st.session_state.player_id if st.session_state.player_id else "")
    conn = sqlite3.connect('poker_data.db')
    u_chk = conn.execute("SELECT role, password FROM Members WHERE pf_id = ?", (p_id,)).fetchone()
    invite_cfg = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'reg_invite_code'").fetchone() or ("888",))[0]
    conn.close()
    if p_id and u_chk:
        if st.text_input("密碼", type="password", key="login_pw") == u_chk[1]:
            if st.button("啟動系統"): st.session_state.player_id, st.session_state.access_level = p_id, u_chk[0]; st.rerun()
    elif p_id:
        with st.form("reg"):
            rn, rpw, ri = st.text_input("暱稱"), st.text_input("密碼", type="password"), st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                cr = sqlite3.connect('poker_data.db'); cr.execute("INSERT INTO Members (pf_id, name, role, xp, password) VALUES (?,?,?,?,?)", (p_id, rn, "玩家", 0, rpw)); cr.commit(); cr.close(); st.success("註冊成功！")
    if st.button("退出王國"): st.session_state.player_id = None; st.rerun()

if not st.session_state.player_id:
    st.markdown(f"""
        <div class="welcome-wall">
            <div class="welcome-title">PRO POKER</div>
            <div class="welcome-subtitle">撲 克 傳 奇 殿 堂</div>
            <div class="feature-box"><b style="color:#FFD700; font-size:1.2em;">🧧 領主認證通道</b><br>輸入 POKERFANS ID 通過邀請碼驗證即可加入王國領地。</div>
            <div class="feature-box"><b style="color:#FFD700; font-size:1.2em;">🎰 幸運獎項抽取</b><br>參與比賽累積 XP，物理抽取實體精美物資。</div>
            <div class="feature-box"><b style="color:#FFD700; font-size:1.2em;">🛡️ 黑金物理核銷</b><br>物資由指揮部精確辨識序號有效性，保障獲獎權益。</div>
            <p style="margin-top:40px; color:#AAA;">請在側邊欄登入以啟動殿堂功能</p>
        </div>
    """, unsafe_allow_html=True); st.stop()

# --- 4. 玩家主介面 ---
conn = sqlite3.connect('poker_data.db')
curr_m = datetime.now().strftime("%m")
t_p = st.tabs(["🪪 會員卡", "🎰 轉盤抽獎", "⚔️ 軍火清冊", "🏆 榮耀榜"])

with t_p[0]:
    u_row = pd.read_sql_query("SELECT * FROM Members WHERE pf_id=?", conn, params=(st.session_state.player_id,)).iloc[0]
    h_pts = (conn.execute("SELECT hero_points FROM Leaderboard WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    m_pts = (conn.execute("SELECT monthly_points FROM Monthly_God WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    h_rk = conn.execute("SELECT COUNT(*) + 1 FROM Leaderboard WHERE hero_points > ?", (h_pts,)).fetchone()[0]
    st.markdown(f'''<div class="rank-card">
        <p style="color:#FFD700; margin:0;">永久 XP 餘額</p>
        <p class="xp-main">{u_row['xp']:,.0f}</p>
        <p class="xp-sub">紅利: {u_row['xp_temp']:,.0f}</p>
        <div class="stats-box">
            <div>🏆 英雄積分: {h_pts:,} (排名:{h_rk})</div>
            <div>🔥 本月戰力: {m_pts:,}</div>
        </div>
        <p style="color:gold; font-size:1.8em; margin-top:20px;">{get_rank_v2500(h_pts)}</p>
    </div>''', unsafe_allow_html=True)
    if st.button("🎰 幸運簽到"):
        conn.execute("UPDATE Members SET xp_temp = xp_temp + 10 WHERE pf_id = ?", (st.session_state.player_id,))
        conn.commit(); st.rerun()
    st.write("---"); st.markdown("#### 🎫 我的獲獎序號 (已核銷可刪除)"); myp = pd.read_sql_query("SELECT id, prize_name, status FROM Prizes WHERE player_id=? ORDER BY id DESC", conn, params=(st.session_state.player_id,))
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
                for i in range(100): time.sleep(0.01); pb.progress(i + 1)
                win = random.choices(inv.to_dict('records'), weights=[float(w) for w in inv['weight'].tolist()], k=1)[0]
                if u_row['xp_temp'] >= 100: conn.execute("UPDATE Members SET xp_temp = xp_temp - 100 WHERE pf_id = ?", (st.session_state.player_id,))
                else: conn.execute("UPDATE Members SET xp_temp = 0, xp = xp - ? WHERE pf_id = ?", (100 - u_row['xp_temp'], st.session_state.player_id))
                conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (win['item_name'],))
                conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time) VALUES (?, ?, '待兌換', ?)", (st.session_state.player_id, win['item_name'], datetime.now()))
                conn.commit(); st.balloons(); st.success(f"🎰 獲得獎項：{win['item_name']}")
        else: st.warning("XP 不足")

with t_p[2]:
    st.subheader("⚔️ 黑金殿堂：物資清冊展示")
    gun_df = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0 ORDER BY item_value DESC", conn)
    cols = st.columns(3)
    for idx, row in gun_df.iterrows():
        with cols[idx % 3]:
            # 物理對位網路圖片，若無圖片則使用預設圖
            img_src = row['img_url'] if row['img_url'] and row['img_url'].startswith('http') else "https://img.freepik.com/free-vector/modern-poker-chips-background_23-2147883740.jpg"
            st.markdown(f'''<div style="background:#111; border:1px solid #444; border-radius:15px; padding:10px; text-align:center;">
                <img src="{img_src}" style="width:100%; border-radius:10px; height:150px; object-fit:contain; background:#000;">
                <p style="color:#FFD700; font-weight:bold; margin-top:10px; font-size:1.1em;">{row['item_name']}</p>
                <p style="color:#FFF;">價值: {row['item_value']:,} XP</p>
                <p style="color:#666; font-size:0.8em;">庫存: {row['stock']}</p>
            </div>''', unsafe_allow_html=True)

with t_p[3]:
    rk1, rk2 = st.columns(2)
    with rk1:
        st.markdown('<div class="glory-title">🎖️ 菁英總榜</div>', unsafe_allow_html=True)
        ldf = pd.read_sql_query("SELECT player_id as ID, hero_points FROM Leaderboard WHERE ID != '330999' ORDER BY hero_points DESC LIMIT 20", conn)
        if not ldf.empty: ldf['榮耀牌位'] = ldf['hero_points'].apply(get_rank_v2500); st.table(ldf[['ID', '榮耀牌位']])
    with rk2:
        st.markdown(f'<div class="glory-title">🔥 {curr_m}月 巔峰戰力榜</div>', unsafe_allow_html=True)
        m_active = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]
        if m_active == "OFF": st.info("🏆 本月活動暫未開啟，敬請期待下期挑戰！")
        else:
            gdf = pd.read_sql_query("SELECT player_id as ID, monthly_points as 積分 FROM Monthly_God WHERE ID != '330999' ORDER BY 積分 DESC LIMIT 15", conn)
            if gdf.empty: st.warning("⚔️ 目前尚未有英雄上榜，領主們請加把勁！")
            else:
                for i, r in gdf.iterrows():
                    if i == 0: st.markdown(f'<div class="gold-medal">👑 冠軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 1: st.markdown(f'<div class="silver-medal">🥈 亞軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    elif i == 2: st.markdown(f'<div class="bronze-medal">🥉 季軍: {r["ID"]} — {r["積分"]} Pts</div>', unsafe_allow_html=True)
                    else: st.write(f"NO.{i+1}: {r['ID']} — {r['積分']} Pts")

# --- 5. 指揮部 (全量物理鎖死) ---
if st.session_state.access_level in ["老闆", "店長"]:
    st.write("---"); st.header("⚙️ 王國指揮部")
    mt = st.tabs(["📁 精算", "📦 物資", "🚀 空投", "📢 視覺", "🎯 任命", "🗑️ 結算", "📜 核銷", "💾 備份"])

    with mt[0]:
        up = st.file_uploader("上傳報表", type="csv")
        if up and st.button("🚀 執行精算"):
            df_c = pd.read_csv(up); df_c.columns = df_c.columns.str.strip(); conn_c = sqlite3.connect('poker_data.db')
            if conn_c.execute("SELECT 1 FROM Import_History WHERE filename = ?", (up.name,)).fetchone(): st.error("❌ 檔案重複匯入！")
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
                conn_c.commit(); st.success("精算對位完成")
            conn_c.close()

    with mt[1]: # --- 【物理修正：網路圖空連結】 ---
        with st.form("ni"):
            nn, nv, ns, nw, n_mx = st.text_input("物資名"), st.number_input("價值", 0), st.number_input("庫存", 0), st.number_input("權重", 10.0), st.number_input("門檻", 0)
            img_url_input = st.text_input("圖片網路連結 (http/https)")
            if st.form_submit_button("🔨 執行物理上架"):
                conn.execute("INSERT OR REPLACE INTO Inventory VALUES (?,?,?,?,?,?)", (nn, ns, nv, nw, img_url_input, n_mx)); conn.commit(); st.rerun()
        st.write("---"); mdf = pd.read_sql_query("SELECT * FROM Inventory", conn)
        for _, ri in mdf.iterrows():
            with st.expander(f"📦 管理：{ri['item_name']}"):
                eq, ew = st.number_input("補貨", 0, key=f"q_{ri['item_name']}"), st.number_input("權重", value=ri['weight'], key=f"w_{ri['item_name']}")
                new_url = st.text_input("更新圖片連結", value=ri['img_url'], key=f"url_{ri['item_name']}")
                if st.button("💾 更新", key=f"u_{ri['item_name']}"): 
                    conn.execute("UPDATE Inventory SET stock=stock+?, weight=?, img_url=? WHERE item_name=?", (eq, ew, new_url, ri['item_name'])); conn.commit(); st.rerun()
                if st.button("🗑️ 下架", key=f"d_{ri['item_name']}"): conn.execute("DELETE FROM Inventory WHERE item_name=?", (ri['item_name'],)); conn.commit(); st.rerun()

    with mt[2]: # 🚀 空投
        tid = st.text_input("目標玩家 ID (空為全服)"); val = st.number_input("XP 數額", 0)
        if st.button("執行物理空投"):
            if not tid: conn.execute("UPDATE Members SET xp_temp = xp_temp + ?", (val,))
            else: conn.execute("UPDATE Members SET xp_temp = xp_temp + ? WHERE pf_id = ?", (val, tid))
            conn.commit(); st.success("成功")

    with mt[3]: # 📢 視覺與活動開關
        ns_v = st.slider("跑馬燈速度", 5, 60, 35); ic_v = st.text_input("註冊邀請碼", "888")
        txt_v = st.text_area("公告內容"); bg_v = st.text_input("背景 URL")
        curr_act = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]
        st.write(f"當前月榜狀態: **{'🟢 已開啟' if curr_act=='ON' else '🔴 已關閉'}**")
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔓 開啟月榜"): conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('monthly_active', 'ON')"); conn.commit(); st.rerun()
        with col_act2:
            if st.button("🔒 關閉月榜"): conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('monthly_active', 'OFF')"); conn.commit(); st.rerun()
        if st.button("💾 保存設定"):
            conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_speed',?),('reg_invite_code',?),('marquee_text',?)", (str(ns_v), ic_v, txt_v))
            if bg_v: conn.execute("INSERT OR REPLACE INTO System_Settings VALUES ('welcome_bg_url',?)", (bg_v,))
            conn.commit(); st.rerun()

    with mt[4]: # 🎯 任命
        rid_v = st.text_input("調動 ID"); rl_v = st.selectbox("任命職位", ["玩家", "員工", "店長", "老闆"])
        if st.button("🪄 任命"):
            pws = {"老闆":"kenken520", "店長":"3939889", "員工":"88888", "玩家":"123456"}
            conn.execute("UPDATE Members SET role=?, password=? WHERE pf_id=?", (rl_v, pws[rl_v], rid_v)); conn.commit(); st.success("成功")

    with mt[5]: # 🗑️ 結算
        if st.button("⚖️ 英雄規費削減"): conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 150)"); conn.commit(); st.success("完成")
        if st.button("🔥 粉碎月榜"): conn.execute("DELETE FROM Monthly_God"); conn.commit(); st.rerun()
        if st.button("💀 粉碎總榜"): conn.execute("DELETE FROM Leaderboard WHERE player_id != '330999'"); conn.commit(); st.rerun()

    with mt[6]: # 📜 核銷
        sid_v = st.number_input("輸入序號 ID", value=0, step=1)
        if st.button("🔥 核銷銷帳", type="primary"):
            p_chk = conn.execute("SELECT player_id, prize_name, status FROM Prizes WHERE id=?", (sid_v,)).fetchone()
            if not p_chk: st.error("❌ 查無序號")
            elif p_chk[2] == '已核銷': st.warning("⚠️ 已核銷")
            else:
                conn.execute("UPDATE Prizes SET status='已核銷' WHERE id=?", (sid_v,))
                conn.execute("INSERT INTO Staff_Logs (staff_id, player_id, prize_name, time) VALUES (?,?,?,?)", (st.session_state.player_id, p_chk[0], p_chk[1], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit(); st.success("✅ 核銷完成"); st.rerun()
        ldf_v = pd.read_sql_query("SELECT id, staff_id, player_id, prize_name, time FROM Staff_Logs ORDER BY id DESC LIMIT 15", conn)
        for _, rv in ldf_v.iterrows():
            c_a, c_b = st.columns([5, 1])
            with c_a: st.write(f"[{rv['time']}] {rv['staff_id']} 核銷 {rv['player_id']} 的 {rv['prize_name']}")
            with cb:
                if st.session_state.access_level == "老闆" and st.button("🗑️", key=f"ld_{rv['id']}"):
                    conn.execute("DELETE FROM Staff_Logs WHERE id=?", (rv['id'],)); conn.commit(); st.rerun()

    with mt[7]: # 💾 備份
        if os.path.exists('poker_data.db'):
            with open('poker_data.db', 'rb') as f: st.download_button("📥 下載 DB", f, "Backup.db")
        rf = st.file_uploader("還原", type="db")
        if rf and st.button("強制還原"):
            with open('poker_data.db', 'wb') as f: f.write(rf.getbuffer())
            st.success("成功"); st.rerun()

conn.close()