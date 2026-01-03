import streamlit as st
import pandas as pd
import random
import re
import time
import math
import threading
import io
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 0. 系統核心配置 ---
st.set_page_config(
    page_title="PRO POKER 撲洛王國 (Cloud)", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. Supabase 連線初始化 ---
@st.cache_resource
def init_connection():
    try:
        if "supabase" in st.secrets:
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        st.error("❌ 找不到 secrets 設定。")
        st.stop()
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        st.stop()

supabase: Client = init_connection()

# --- 2. 極速核心：快取與背景執行 (解決卡頓的關鍵) ---

@st.cache_data(ttl=600)
def get_all_settings():
    """快取系統設定，減少重複連線"""
    try:
        response = supabase.table("System_Settings").select("*").execute()
        return {item['config_key']: item['config_value'] for item in response.data}
    except: return {}

system_config = get_all_settings()

def get_config(key, default_value):
    return system_config.get(key, default_value)

def set_config(key, value):
    try:
        supabase.table("System_Settings").upsert({"config_key": key, "config_value": str(value)}).execute()
        get_all_settings.clear()
    except Exception as e: print(f"Config Error: {e}")

def get_current_user_data(player_id):
    """只抓取必要欄位，並優先讀取 session"""
    if 'user_data' not in st.session_state or st.session_state.user_data.get('pf_id') != player_id:
        res = supabase.table("Members").select("pf_id, name, xp, xp_temp, role, vip_level, vip_expiry, vip_points, last_checkin, consecutive_days").eq("pf_id", player_id).execute()
        if res.data: st.session_state.user_data = res.data[0]
        else: return None
    return st.session_state.user_data

# 背景執行緒：寫入資料庫
def _bg_update_xp(pid, amount):
    try:
        cur = supabase.table("Members").select("xp").eq("pf_id", pid).execute().data[0]['xp']
        supabase.table("Members").update({"xp": cur + amount}).eq("pf_id", pid).execute()
    except: pass

def _bg_log_game(pid, game, action, amount):
    try:
        supabase.table("Game_Transactions").insert({
            "player_id": pid, "game_type": game, "action_type": action, 
            "amount": amount, "timestamp": datetime.now().isoformat()
        }).execute()
    except: pass

def update_user_xp(player_id, amount):
    """極速更新：UI 瞬間更新 + 背景存檔"""
    if 'user_data' in st.session_state:
        st.session_state.user_data['xp'] += amount
    threading.Thread(target=_bg_update_xp, args=(player_id, amount)).start()

def log_game_transaction(player_id, game, action, amount):
    threading.Thread(target=_bg_log_game, args=(player_id, game, action, amount)).start()

# --- 3. UI 初始化 ---
def init_flagship_ui():
    m_spd = get_config('marquee_speed', "35")
    m_bg = get_config('welcome_bg_url', "https://img.freepik.com/free-photo/poker-table-dark-atmosphere_23-2151003784.jpg")
    m_title = get_config('welcome_title', "PRO POKER")
    m_subtitle = get_config('welcome_subtitle', "撲 洛 傳 奇 殿 堂")
    m_txt = get_config('marquee_text', "撲洛王國營運中，歡迎回歸領地！")
    
    lb_title_1 = get_config('leaderboard_title_1', "🎖️ 菁英總榜")
    lb_title_2 = get_config('leaderboard_title_2', "🔥 月度戰神")
    
    m_desc1 = get_config('lobby_desc_1', "♠️ 頂級賽事體驗")
    m_desc2 = get_config('lobby_desc_2', "♥ 公平公正競技")
    m_desc3 = get_config('lobby_desc_3', "♦ 專屬尊榮服務")
    
    ci_min = int(get_config('checkin_min', "10"))
    ci_max = int(get_config('checkin_max', "500"))

    if get_config('marquee_mode', "custom") == 'auto' and random.random() < 0.2:
        try:
            res = supabase.table("Prizes").select("prize_name, source, player_id").order("id", desc=True).limit(1).execute()
            if res.data:
                row = res.data[0]
                if "大獎" in str(row['prize_name']) or "XP" in str(row['prize_name']):
                    m_txt = f"🎉 恭喜玩家 {row['player_id']} 在 {row['source']} 獲得 {row['prize_name']}！"
        except: pass

    st.markdown(f"""
        <style>
            :root {{ color-scheme: dark; }}
            html, body, .stApp {{ background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Arial', sans-serif; }}
            .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea {{ background-color: #1a1a1a !important; color: #FFFFFF !important; border: 1px solid #444 !important; border-radius: 8px !important; }}
            .stButton > button {{ background: linear-gradient(180deg, #333 0%, #111 100%) !important; color: #FFD700 !important; border: 1px solid #FFD700 !important; border-radius: 8px !important; font-weight: bold !important; transition: 0.1s; }}
            .stButton > button:hover {{ background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%) !important; color: #000 !important; transform: scale(1.02); }}
            .stTabs [data-baseweb="tab-list"] {{ gap: 5px; background-color: #111; padding: 10px; border-radius: 15px; border: 1px solid #333; }}
            .stTabs [data-baseweb="tab"] {{ background-color: #222; color: #AAA; border-radius: 8px; border: none; }}
            .stTabs [aria-selected="true"] {{ background-color: #FFD700 !important; color: #000 !important; font-weight: bold; }}
            .rank-card {{ background: linear-gradient(135deg, #1a1a1a 0%, #000 100%); border: 2px solid #FFD700; border-radius: 20px; padding: 25px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-card {{ background: linear-gradient(135deg, #000 0%, #222 100%); border: 2px solid #9B30FF; border-radius: 20px; padding: 25px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-badge {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000; padding: 5px 15px; border-radius: 15px; font-weight: 900; display: inline-block; margin-bottom: 15px; }}
            .mall-card {{ background: #151515; border: 1px solid #333; border-radius: 12px; padding: 15px; text-align: center; height: 100%; display:flex; flex-direction:column; justify-content:space-between; }}
            .lobby-card {{ background: linear-gradient(145deg, #222, #111); border: 1px solid #444; border-radius: 15px; padding: 20px; text-align: center; cursor: pointer; transition: 0.2s; }}
            .lobby-card:hover {{ border-color: #FFD700; transform: scale(1.02); }}
            .lobby-icon {{ font-size: 3em; margin-bottom: 10px; }}
            .marquee-container {{ background: #1a1a1a; color: #FFD700; padding: 12px 0; overflow: hidden; white-space: nowrap; border-top: 2px solid #FFD700; border-bottom: 2px solid #FFD700; margin-bottom: 25px; }}
            .marquee-text {{ display: inline-block; padding-left: 100%; animation: marquee {m_spd}s linear infinite; font-size: 1.5em; font-weight: bold; }}
            @keyframes marquee {{ 0% {{ transform: translate(0, 0); }} 100% {{ transform: translate(-100%, 0); }} }}
            
            .bacc-zone {{ border: 2px solid; border-radius: 10px; padding: 10px; margin: 5px; min-height: 120px; background-color: rgba(0,0,0,0.3); display:flex; flex-direction:column; align-items:center; justify-content:center; cursor:pointer; transition:0.2s; }}
            .bacc-player {{ border-color: #00BFFF; }}
            .bacc-banker {{ border-color: #FF4444; }}
            .bacc-tie {{ border-color: #00FF00; }}
            .bacc-card {{ background-color: #FFF; color: #000; border-radius: 5px; width: 40px; height: 60px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.1em; margin: 2px; }}
            .bacc-card.red {{ color: #D40000; }}
            .bacc-card.black {{ color: #000000; }}
            
            .mine-btn {{ width: 100%; aspect-ratio: 1; border-radius: 8px; border: 2px solid #444; background: #222; font-size: 1.5em; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.1s; }}
            .mine-btn:active {{ transform: scale(0.95); background: #444; }}
        </style>
        <div class="welcome-wall" style="text-align:center; padding:60px 20px; background:linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.9)), url('{m_bg}'); background-size:cover; border-radius:20px; border:2px solid #FFD700; margin-bottom:20px;">
            <div style="font-size:3.5em; font-weight:900; color:#FFD700;">{m_title}</div>
            <div style="font-size:1.5em; color:#EEE;">{m_subtitle}</div>
            <div style="margin-top:20px;">
                <span style="display:inline-block; margin:5px; padding:8px 15px; border:1px solid #555; border-radius:20px; background:rgba(0,0,0,0.5);">{m_desc1}</span>
                <span style="display:inline-block; margin:5px; padding:8px 15px; border:1px solid #555; border-radius:20px; background:rgba(0,0,0,0.5);">{m_desc2}</span>
                <span style="display:inline-block; margin:5px; padding:8px 15px; border:1px solid #555; border-radius:20px; background:rgba(0,0,0,0.5);">{m_desc3}</span>
            </div>
        </div>
        <div class="marquee-container"><div class="marquee-text">{m_txt}</div></div>
    """, unsafe_allow_html=True)
    return lb_title_1, lb_title_2, ci_min, ci_max

def get_rank_v2500(pts):
    if pts >= int(get_config('rank_limit_challenger', "1000")): return "🏆 菁英"
    elif pts >= int(get_config('rank_limit_master', "500")): return "🎖️ 大師"
    elif pts >= int(get_config('rank_limit_diamond', "200")): return "💎 鑽石"
    elif pts >= int(get_config('rank_limit_platinum', "80")): return "⬜ 白金"
    else: return "🥈 白銀"

def rank_to_level(rank_str):
    if "菁英" in rank_str: return 5
    if "大師" in rank_str: return 4
    if "鑽石" in rank_str: return 3
    if "白金" in rank_str: return 2
    return 1

def validate_nickname(nickname):
    if not nickname or not nickname.strip(): return False, "暱稱不可為空"
    is_ascii = all(ord(c) < 128 for c in nickname)
    if is_ascii:
        if len(nickname) > 10: return False, "英文暱稱不可超過 10 個字母"
    else:
        if len(nickname) > 6: return False, "中文暱稱不可超過 6 個字"
    return True, "OK"

def get_vip_bonus(level):
    return float(get_config(f'vip_bonus_{level}', "0"))

def get_vip_discount(level):
    return float(get_config(f'vip_discount_{level}', "0"))

def check_mission_status(player_id, m_type, criteria, target_val, mission_id):
    now = datetime.now()
    m_res = supabase.table("Missions").select("*").eq("id", mission_id).execute()
    if not m_res.data: return False, False, 0
    m_row = m_res.data[0]
    
    if m_row.get('time_limit_months', 0) > 0:
        mem = supabase.table("Members").select("join_date").eq("pf_id", player_id).execute()
        if mem.data and mem.data[0]['join_date']:
             try:
                 jd = datetime.strptime(mem.data[0]['join_date'], "%Y-%m-%d")
                 if (now - jd).days > (m_row['time_limit_months'] * 30): return False, False, 0
             except: pass
    
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if m_type == "Weekly": start_time = now - timedelta(days=now.weekday())
    elif m_type == "Monthly": start_time = now.replace(day=1)
    elif m_type == "Season": start_time = datetime(2020, 1, 1) 
    
    claimed = False
    log_res = supabase.table("Mission_Logs").select("claim_time").eq("player_id", player_id).eq("mission_id", mission_id).order("claim_time", desc=True).limit(1).execute()
    if log_res.data:
        last_claim_str = log_res.data[0]['claim_time']
        try:
            last_claim = datetime.fromisoformat(last_claim_str.replace('Z', '+00:00')).replace(tzinfo=None)
            if m_row.get('recurring_months', 0) > 0:
                 if (now - last_claim).days < (m_row['recurring_months'] * 30): claimed = True
            else:
                 if last_claim >= start_time: claimed = True
        except: pass

    current_val = 0
    met = False
    
    if criteria == "daily_checkin":
        mem = supabase.table("Members").select("last_checkin").eq("pf_id", player_id).execute()
        if mem.data and mem.data[0]['last_checkin']:
            if mem.data[0]['last_checkin'].startswith(now.strftime("%Y-%m-%d")): met = True; current_val = 1
            
    elif criteria == "consecutive_checkin":
        mem = supabase.table("Members").select("consecutive_days").eq("pf_id", player_id).execute()
        if mem.data:
            cons = mem.data[0]['consecutive_days'] or 0
            current_val = cons; met = cons >= target_val
            
    elif criteria == "daily_win":
        res = supabase.table("Prizes").select("id", count="exact").eq("player_id", player_id).ilike("source", "GameWin%").gte("time", now.strftime("%Y-%m-%d 00:00:00")).execute()
        cnt = res.count or 0
        current_val = min(cnt, target_val); met = cnt >= target_val
        
    elif criteria == "game_play_count":
        res = supabase.table("Game_Transactions").select("id", count="exact").eq("player_id", player_id).eq("action_type", "BET").gte("timestamp", start_time.isoformat()).execute()
        cnt = res.count or 0
        current_val = cnt; met = cnt >= target_val
        
    elif criteria == "tournament_count":
        res = supabase.table("Tournament_Records").select("id", count="exact").eq("player_id", player_id).gte("time", start_time.isoformat()).execute()
        cnt = res.count or 0
        current_val = cnt; met = cnt >= target_val
        
    elif criteria == "monthly_days":
        res = supabase.table("Tournament_Records").select("time").eq("player_id", player_id).gte("time", start_time.isoformat()).execute()
        if res.data:
            dates = set(d['time'].split('T')[0] for d in res.data)
            cnt = len(dates)
            current_val = cnt; met = cnt >= target_val
            
    elif criteria == "rank_level":
        lb = supabase.table("Leaderboard").select("hero_points").eq("player_id", player_id).execute()
        pts = lb.data[0]['hero_points'] if lb.data else 0
        curr_lvl = rank_to_level(get_rank_v2500(pts))
        current_val = curr_lvl; met = curr_lvl >= target_val
        
    elif criteria == "vip_level":
        mem = supabase.table("Members").select("vip_level").eq("pf_id", player_id).execute()
        curr_vip = mem.data[0]['vip_level'] if mem.data else 0
        current_val = curr_vip; met = curr_vip >= target_val
        
    elif criteria == "vip_duration":
        mem = supabase.table("Members").select("vip_expiry").eq("pf_id", player_id).execute()
        if mem.data and mem.data[0]['vip_expiry']:
            try:
                exp_dt = datetime.strptime(mem.data[0]['vip_expiry'].split('.')[0], "%Y-%m-%d %H:%M:%S")
                if exp_dt > now:
                    days = (exp_dt - now).days
                    current_val = days; met = days >= target_val
            except: pass

    return met, claimed, current_val

# --- 4. 登入與側邊欄 ---
if "player_id" not in st.session_state:
    st.session_state.player_id = None
    st.session_state.access_level = "玩家"

try:
    tk = st.query_params.get("token")
    if tk and st.session_state.player_id is None:
        st.session_state.prefill_id = tk
except: pass

with st.sidebar:
    st.title("🛡️ 認證總部")
    cur_id = st.session_state.get('prefill_id', "")
    p_id_input = st.text_input("POKERFANS ID", value=cur_id)
    
    u_chk = None
    if p_id_input:
        res = supabase.table("Members").select("role, password").eq("pf_id", p_id_input).execute()
        if res.data: u_chk = res.data[0]
            
    invite_cfg = get_config('reg_invite_code', "888")
    
    if p_id_input and u_chk:
        login_pw = st.text_input("密碼", type="password", key="sidebar_pw")
        if st.button("登入Pro撲克殿堂"):
            if login_pw == u_chk['password']:
                st.session_state.player_id = p_id_input
                st.session_state.access_level = u_chk['role']
                if 'user_data' in st.session_state: del st.session_state.user_data
                get_current_user_data(p_id_input)
                st.query_params["token"] = p_id_input
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    elif p_id_input:
        with st.form("reg_sidebar"):
            st.info("⚠️ 首次註冊/認領")
            rn = st.text_input("暱稱"); rpw = st.text_input("密碼", type="password"); ri = st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                if rn:
                    exist = supabase.table("Members").select("*").eq("pf_id", p_id_input).execute()
                    if exist.data and (not exist.data[0]['password']):
                         supabase.table("Members").update({"name": rn, "password": rpw, "role": "玩家", "join_date": datetime.now().strftime("%Y-%m-%d")}).eq("pf_id", p_id_input).execute()
                         st.success("✅ 帳號認領成功！")
                    else:
                         try:
                             supabase.table("Members").insert({"pf_id": p_id_input, "name": rn, "role": "玩家", "xp": 0, "password": rpw, "join_date": datetime.now().strftime("%Y-%m-%d")}).execute()
                             st.success("✅ 註冊成功！")
                         except: st.error("❌ 該 ID 已被註冊。")
                else: st.error("請輸入暱稱")

    if st.session_state.player_id:
        if st.button("🚪 退出王國"): 
            st.session_state.player_id = None
            if 'user_data' in st.session_state: del st.session_state.user_data
            st.query_params.clear()
            st.rerun()

lb_title_1, lb_title_2, ci_min, ci_max = init_flagship_ui()

if not st.session_state.player_id: st.stop()

# --- 5. 主程式 ---
u_row = get_current_user_data(st.session_state.player_id)
t_p = st.tabs(["🪪 排位/VIP", "🎯 任務", "🎮 遊戲大廳", "🛒 商城", "🎒 背包", "🏆 榜單"])

with t_p[0]: # 排位卡
    h_res = supabase.table("Leaderboard").select("hero_points").eq("player_id", st.session_state.player_id).execute()
    h_pts = h_res.data[0]['hero_points'] if h_res.data else 0
    m_res = supabase.table("Monthly_God").select("monthly_points").eq("player_id", st.session_state.player_id).execute()
    m_pts = m_res.data[0]['monthly_points'] if m_res.data else 0
    
    player_rank_title = get_rank_v2500(h_pts)
    vip_lvl = int(u_row.get('vip_level', 0) or 0)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'''<div class="vip-card"><h3>{u_row['name']}</h3><p>ID: {u_row['pf_id']}</p><h2>VIP {vip_lvl}</h2><p>VP: {u_row.get('vip_points', 0):,.0f}</p></div>''', unsafe_allow_html=True)
    with c2:
        st.markdown(f'''<div class="rank-card"><h3>{player_rank_title}</h3><h1 style="color:#00FF00;">💎 {u_row['xp']:,.0f}</h1><p>積分: {h_pts}</p><p>月積分: {m_pts}</p></div>''', unsafe_allow_html=True)

    if st.button("🎰 幸運簽到"):
        today = datetime.now().strftime("%Y-%m-%d")
        if str(u_row.get('last_checkin', '')).startswith(today): st.warning("⚠️ 已簽到")
        else:
            base = random.randint(ci_min, ci_max)
            bonus = int(base * (1 + float(get_config(f'vip_bonus_{vip_lvl}', "0"))/100))
            
            update_user_xp(st.session_state.player_id, bonus)
            st.session_state.user_data['last_checkin'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            threading.Thread(target=lambda: supabase.table("Members").update({"last_checkin": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).eq("pf_id", st.session_state.player_id).execute()).start()
            threading.Thread(target=lambda: supabase.table("Prizes").insert({"player_id": st.session_state.player_id, "prize_name": f"{bonus} XP", "status": "自動入帳", "time": datetime.now().isoformat(), "source": "DailyCheckIn"}).execute()).start()
            
            st.success(f"✅ 簽到成功！獲得 {bonus} XP"); st.rerun()

with t_p[1]: # 任務
    st.subheader("🎯 任務中心")
    missions = supabase.table("Missions").select("*").eq("status", "Active").execute().data
    for m in missions:
        is_met, is_claimed, cur_val = check_mission_status(st.session_state.player_id, m['type'], m['target_criteria'], m['target_value'], m['id'])
        c1, c2 = st.columns([4, 1])
        c1.info(f"**{m['title']}** - 獎勵: {m['reward_xp']} XP (進度: {cur_val}/{m['target_value']})")
        if is_claimed: c2.button("已領取", key=f"mc_{m['id']}", disabled=True)
        elif is_met:
            if c2.button("領取", key=f"m_{m['id']}"):
                update_user_xp(st.session_state.player_id, m['reward_xp'])
                supabase.table("Mission_Logs").insert({"player_id": st.session_state.player_id, "mission_id": m['id'], "claim_time": datetime.now().isoformat()}).execute()
                st.success("已領取"); st.rerun()
        else: c2.button("未達成", key=f"ml_{m['id']}", disabled=True)

with t_p[2]: # 遊戲大廳
    st.markdown(f'<div class="xp-bar">💰 餘額: {u_row["xp"]:,} XP</div>', unsafe_allow_html=True)
    if 'current_game' not in st.session_state: st.session_state.current_game = 'lobby'
    
    if st.session_state.current_game == 'lobby':
        c1, c2, c3 = st.columns(3)
        if c1.button("💣 掃雷", use_container_width=True): st.session_state.current_game = 'mines'; st.rerun()
        if c2.button("🎡 轉盤", use_container_width=True): st.session_state.current_game = 'wheel'; st.rerun()
        if c3.button("♠️ 21點", use_container_width=True): st.session_state.current_game = 'blackjack'; st.rerun()
        c4, c5 = st.columns(2)
        if c4.button("🏛️ 百家樂", use_container_width=True): st.session_state.current_game = 'baccarat'; st.rerun()
        if c5.button("🔴 輪盤", use_container_width=True): st.session_state.current_game = 'roulette'; st.rerun()

    else:
        if st.button("⬅️ 返回大廳"): st.session_state.current_game = 'lobby'; st.rerun()

        # --- 掃雷 (極速版) ---
        if st.session_state.current_game == 'mines':
            st.subheader("💣 撲洛掃雷")
            if 'mines_active' not in st.session_state: st.session_state.mines_active = False
            if 'mines_revealed' not in st.session_state or len(st.session_state.mines_revealed) != 25:
                st.session_state.mines_revealed = [False] * 25
                st.session_state.mines_grid = [0] * 25 # 0=Safe, 1=Mine
                st.session_state.mines_active = False
            
            if not st.session_state.mines_active:
                c1, c2 = st.columns(2)
                bet = c1.number_input("投入 XP", 100, 10000, 100)
                mines = c2.slider("地雷數", 1, 24, 3)
                if st.button("🚀 開始"):
                    if u_row['xp'] >= bet:
                        update_user_xp(st.session_state.player_id, -bet)
                        log_game_transaction(st.session_state.player_id, 'mines', 'BET', bet)
                        st.session_state.mines_active = True
                        st.session_state.mines_game_over = False
                        st.session_state.mines_bet = bet
                        st.session_state.mines_revealed = [False] * 25
                        st.session_state.mines_grid = [0]*(25-mines) + [1]*mines
                        random.shuffle(st.session_state.mines_grid)
                        st.rerun()
                    else: st.error("XP 不足")
            else:
                rev_count = sum(1 for i, r in enumerate(st.session_state.mines_revealed) if r and st.session_state.mines_grid[i] == 0)
                mine_count = sum(st.session_state.mines_grid)
                try: mult = 0.97 * (math.comb(25, rev_count) / math.comb(25 - mine_count, rev_count))
                except: mult = 1.0
                cur_win = int(st.session_state.mines_bet * mult)
                
                c_info, c_cash = st.columns([3, 1])
                c_info.info(f"倍率: {mult:.2f}x | 贏取: {cur_win}")
                if c_cash.button("💰 結算領錢"):
                    update_user_xp(st.session_state.player_id, cur_win)
                    log_game_transaction(st.session_state.player_id, 'mines', 'WIN', cur_win)
                    st.session_state.mines_active = False
                    st.success(f"贏得 {cur_win} XP"); time.sleep(1); st.rerun()

                cols = st.columns(5)
                for i in range(25):
                    with cols[i%5]:
                        if st.session_state.mines_revealed[i]:
                            if st.session_state.mines_grid[i] == 1: st.button("💥", key=f"m_{i}", disabled=True)
                            else: st.button("💎", key=f"m_{i}", disabled=True)
                        else:
                            if st.button("❓", key=f"m_{i}"):
                                st.session_state.mines_revealed[i] = True
                                if st.session_state.mines_grid[i] == 1:
                                    st.session_state.mines_active = False
                                    st.session_state.mines_game_over = True
                                    st.error("爆炸了！")
                                st.rerun()
                if st.session_state.get('mines_game_over'):
                    if st.button("再來一局"): st.rerun()

        # --- 轉盤 ---
        elif st.session_state.current_game == 'wheel':
            st.subheader("🎡 幸運轉盤")
            cost = int(get_config('min_bet_wheel', "100"))
            st.info(f"每次消耗: {cost} XP")
            if st.button("🚀 啟動"):
                if u_row['xp'] >= cost:
                    update_user_xp(st.session_state.player_id, -cost)
                    log_game_transaction(st.session_state.player_id, 'wheel', 'BET', cost)
                    
                    roll = random.random()
                    win_xp = 0
                    if roll < 0.1: win_xp = cost * 5; msg = "大獎！5倍！"
                    elif roll < 0.4: win_xp = cost * 2; msg = "中獎！2倍！"
                    else: msg = "銘謝惠顧"
                    
                    if win_xp > 0:
                        update_user_xp(st.session_state.player_id, win_xp)
                        log_game_transaction(st.session_state.player_id, 'wheel', 'WIN', win_xp)
                        st.balloons()
                    st.success(f"結果: {msg}")
                else: st.error("XP 不足")

        # --- 21點 ---
        elif st.session_state.current_game == 'blackjack':
            st.subheader("♠️ 21點")
            if 'bj_active' not in st.session_state: st.session_state.bj_active = False
            
            if not st.session_state.bj_active:
                bet = st.number_input("下注", 100, 10000, 100)
                if st.button("發牌"):
                    if u_row['xp'] >= bet:
                        update_user_xp(st.session_state.player_id, -bet)
                        log_game_transaction(st.session_state.player_id, 'blackjack', 'BET', bet)
                        st.session_state.bj_active = True
                        st.session_state.bj_bet = bet
                        st.session_state.bj_deck = [(r,s) for r in ['2','3','4','5','6','7','8','9','10','J','Q','K','A'] for s in ['♠','♥','♦','♣']]
                        random.shuffle(st.session_state.bj_deck)
                        st.session_state.bj_p = [st.session_state.bj_deck.pop(), st.session_state.bj_deck.pop()]
                        st.session_state.bj_d = [st.session_state.bj_deck.pop(), st.session_state.bj_deck.pop()]
                        st.rerun()
            else:
                def hand_val(h):
                    v = 0; aces = 0
                    for r, s in h:
                        if r in ['J','Q','K']: v+=10
                        elif r == 'A': v+=11; aces+=1
                        else: v+=int(r)
                    while v > 21 and aces: v-=10; aces-=1
                    return v
                
                ph = hand_val(st.session_state.bj_p)
                st.write(f"莊家: {st.session_state.bj_d[0]} + ?")
                st.write(f"你: {st.session_state.bj_p} ({ph})")
                
                if ph > 21:
                    st.error("爆牌！輸了")
                    if st.button("再來"): st.session_state.bj_active = False; st.rerun()
                else:
                    c1, c2 = st.columns(2)
                    if c1.button("要牌"):
                        st.session_state.bj_p.append(st.session_state.bj_deck.pop())
                        st.rerun()
                    if c2.button("停牌"):
                        while hand_val(st.session_state.bj_d) < 17:
                            st.session_state.bj_d.append(st.session_state.bj_deck.pop())
                        final_d = hand_val(st.session_state.bj_d)
                        win = 0
                        if final_d > 21 or ph > final_d: win = 2
                        elif ph == final_d: win = 1
                        
                        if win > 0:
                            amt = int(st.session_state.bj_bet * win)
                            update_user_xp(st.session_state.player_id, amt)
                            log_game_transaction(st.session_state.player_id, 'blackjack', 'WIN', amt)
                            st.success(f"贏了 {amt}!")
                        else: st.error("莊家勝")
                        st.session_state.bj_active = False

        # --- 百家樂 (完整復刻) ---
        elif st.session_state.current_game == 'baccarat':
            st.subheader("🏛️ 皇家百家樂")
            if 'bacc_chips' not in st.session_state: st.session_state.bacc_chips = 100
            if 'bacc_bets' not in st.session_state: st.session_state.bacc_bets = {"P":0, "B":0, "T":0, "PP":0, "BP":0}
            
            # 讀取路單 (背景)
            try:
                state = supabase.table("Baccarat_Global").select("*").eq("id", 1).execute().data[0]
                hist_list = state['history_string'].split(',') if state['history_string'] else []
            except: hist_list = []

            st.write("#### 📜 牌路")
            st.write(" ".join(hist_list[-20:])) # 簡易顯示

            chips = [100, 500, 1000, 5000, 10000]
            c_cols = st.columns(5)
            for i, c in enumerate(chips):
                if c_cols[i].button(str(c)): st.session_state.bacc_chips = c
            st.info(f"當前籌碼: {st.session_state.bacc_chips}")

            c1, c2, c3, c4, c5 = st.columns(5)
            def add_bet(t): st.session_state.bacc_bets[t] += st.session_state.bacc_chips
            
            with c1: 
                st.button("閒 (1:1)", on_click=add_bet, args=("P",), use_container_width=True)
                st.write(f"下注: {st.session_state.bacc_bets['P']}")
            with c2: 
                st.button("莊 (1:0.95)", on_click=add_bet, args=("B",), use_container_width=True)
                st.write(f"下注: {st.session_state.bacc_bets['B']}")
            with c3: 
                st.button("和 (1:8)", on_click=add_bet, args=("T",), use_container_width=True)
                st.write(f"下注: {st.session_state.bacc_bets['T']}")
            with c4: st.button("閒對", on_click=add_bet, args=("PP",), use_container_width=True)
            with c5: st.button("莊對", on_click=add_bet, args=("BP",), use_container_width=True)

            if st.button("💰 發牌", type="primary"):
                total = sum(st.session_state.bacc_bets.values())
                if total > 0 and u_row['xp'] >= total:
                    update_user_xp(st.session_state.player_id, -total)
                    log_game_transaction(st.session_state.player_id, 'baccarat', 'BET', total)
                    
                    deck = [1,2,3,4,5,6,7,8,9,10,11,12,13] * 8; random.shuffle(deck)
                    p_hand = [deck.pop(), deck.pop()]; b_hand = [deck.pop(), deck.pop()]
                    def get_val(h): return sum([0 if c>=10 else c for c in h]) % 10
                    if get_val(p_hand) < 8 and get_val(b_hand) < 8:
                        if get_val(p_hand) <= 5: p_hand.append(deck.pop())
                        if get_val(b_hand) <= 5: b_hand.append(deck.pop())
                    
                    p_val = get_val(p_hand); b_val = get_val(b_hand)
                    winner = "T"
                    if p_val > b_val: winner = "P"
                    elif b_val > p_val: winner = "B"
                    
                    payout = 0
                    if winner == "P": payout += st.session_state.bacc_bets['P'] * 2
                    if winner == "B": payout += int(st.session_state.bacc_bets['B'] * 1.95)
                    if winner == "T": payout += st.session_state.bacc_bets['T'] * 9
                    if winner == "T": payout += st.session_state.bacc_bets['P'] + st.session_state.bacc_bets['B'] # 退回
                    
                    if payout > 0:
                        update_user_xp(st.session_state.player_id, payout)
                        log_game_transaction(st.session_state.player_id, 'baccarat', 'WIN', payout)
                        st.success(f"贏得 {payout} XP！結果: {winner}")
                    else: st.error(f"莊家吃！結果: {winner}")
                    
                    # 背景更新路單
                    new_h = (hist_list + [winner])[-60:]
                    threading.Thread(target=lambda: supabase.table("Baccarat_Global").update({"history_string": ",".join(new_h)}).eq("id", 1).execute()).start()
                    st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                else: st.error("餘額不足或未下注")

        # --- 輪盤 (完整復刻) ---
        elif st.session_state.current_game == 'roulette':
            st.subheader("🔴 俄羅斯輪盤")
            if 'roulette_bets' not in st.session_state: st.session_state.roulette_bets = {} 
            if 'roulette_chips' not in st.session_state: st.session_state.roulette_chips = 100
            
            chips = [100, 500, 1000, 5000, 10000]
            c_cols = st.columns(5)
            for i, c in enumerate(chips):
                if c_cols[i].button(str(c), key=f"r_c_{c}"): st.session_state.roulette_chips = c
            
            st.info(f"當前籌碼: {st.session_state.roulette_chips} | 總下注: {sum(st.session_state.roulette_bets.values())}")
            
            if st.button("🚀 旋轉 (SPIN)", type="primary"):
                total = sum(st.session_state.roulette_bets.values())
                if total > 0 and u_row['xp'] >= total:
                    update_user_xp(st.session_state.player_id, -total)
                    log_game_transaction(st.session_state.player_id, 'roulette', 'BET', total)
                    
                    final_num = random.randint(0, 36)
                    red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                    total_win = 0
                    
                    for t, amt in st.session_state.roulette_bets.items():
                        win = False
                        if t.isdigit() and int(t) == final_num: win = True; mult = 36
                        elif t == "Red" and final_num in red_nums: win = True; mult = 2
                        elif t == "Black" and final_num not in red_nums and final_num != 0: win = True; mult = 2
                        if win: total_win += amt * mult
                        
                    if total_win > 0:
                        update_user_xp(st.session_state.player_id, total_win)
                        log_game_transaction(st.session_state.player_id, 'roulette', 'WIN', total_win)
                        st.success(f"開出 {final_num}！贏得 {total_win} XP")
                    else: st.error(f"開出 {final_num}，未中獎")
                    st.session_state.roulette_bets = {}
                else: st.error("餘額不足")

            if st.button("清除所有下注"): st.session_state.roulette_bets = {}
            
            # 簡易下注區
            c1, c2, c3 = st.columns(3)
            if c1.button("🔴 紅 (Red)"): st.session_state.roulette_bets["Red"] = st.session_state.roulette_bets.get("Red", 0) + st.session_state.roulette_chips
            if c2.button("⚫ 黑 (Black)"): st.session_state.roulette_bets["Black"] = st.session_state.roulette_bets.get("Black", 0) + st.session_state.roulette_chips
            if c3.button("0 (Green)"): st.session_state.roulette_bets["0"] = st.session_state.roulette_bets.get("0", 0) + st.session_state.roulette_chips

with t_p[3]: # 商城
    st.subheader("🛒 商城")
    @st.cache_data(ttl=60)
    def get_shop_items():
        return supabase.table("Inventory").select("*").execute().data
    
    items = get_shop_items()
    if items:
        for item in items:
            with st.expander(f"{item['item_name']} - ⚡{item['mall_price']}"):
                if st.button("購買", key=f"buy_{item['item_name']}"):
                    if u_row['xp'] >= item['mall_price']:
                        update_user_xp(st.session_state.player_id, -item['mall_price'])
                        supabase.table("Prizes").insert({"player_id": st.session_state.player_id, "prize_name": item['item_name'], "status": "待兌換"}).execute()
                        st.success("購買成功")
                    else: st.error("XP 不足")

with t_p[4]: # 背包
    st.subheader("🎒 背包")
    res = supabase.table("Prizes").select("*").eq("player_id", st.session_state.player_id).eq("status", "待兌換").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['prize_name', 'time', 'source']])
    else: st.info("背包空空如也")

with t_p[5]: # 榜單
    c1, c2 = st.columns(2)
    with c1:
        st.write("🏆 總榜")
        lb = supabase.table("Leaderboard").select("player_id, hero_points").order("hero_points", desc=True).limit(10).execute()
        st.dataframe(pd.DataFrame(lb.data))
    with c2:
        st.write("🔥 月榜")
        mg = supabase.table("Monthly_God").select("player_id, monthly_points").order("monthly_points", desc=True).limit(10).execute()
        st.dataframe(pd.DataFrame(mg.data))

# --- 5. 後台管理 (Admin) ---
if st.session_state.access_level in ["老闆", "店長"]:
    st.write("---"); st.header("⚙️ 指揮部")
    
    with st.expander("🛂 櫃台核銷 (已修復)"):
        tid = st.text_input("玩家 ID")
        if tid:
            prizes = supabase.table("Prizes").select("id, prize_name").eq("player_id", tid).eq("status", "待兌換").execute().data
            if prizes:
                df = pd.DataFrame(prizes)
                st.table(df)
                rid = st.selectbox("核銷 ID", df['id'].tolist())
                if st.button("確認核銷"):
                    supabase.table("Prizes").update({"status": "已核銷"}).eq("id", rid).execute()
                    st.success("已核銷")
            else: st.info("無待核銷物品")
            
            if st.button("充值 1000 XP"):
                update_user_xp(tid, 1000)
                st.success("已充值")

    with st.expander("🚀 物資空投"):
        targets = supabase.table("Members").select("pf_id").execute().data
        all_ids = [t['pf_id'] for t in targets]
        sel_id = st.selectbox("選擇玩家", ["全體"] + all_ids)
        amount = st.number_input("XP 數量", value=100)
        if st.button("發送空投"):
            if sel_id == "全體":
                for pid in all_ids: update_user_xp(pid, amount)
            else:
                update_user_xp(sel_id, amount)
            st.success("空投完畢")

    with st.expander("📁 賽事精算導入"):
        up = st.file_uploader("上傳 CSV/Excel")
        if up and st.button("執行精算"):
            try:
                if up.name.endswith('.csv'): df = pd.read_csv(up)
                else: df = pd.read_excel(up)
                st.write("預覽:", df.head())
                if st.button("確認寫入資料庫"):
                    # 這裡實作導入邏輯，範例：
                    for _, r in df.iterrows():
                        pid = str(r['ID'])
                        pts = int(r['Points'])
                        # 更新排行榜
                        try:
                            cur = supabase.table("Leaderboard").select("hero_points").eq("player_id", pid).execute().data[0]['hero_points']
                            supabase.table("Leaderboard").update({"hero_points": cur + pts}).eq("player_id", pid).execute()
                        except:
                            supabase.table("Leaderboard").insert({"player_id": pid, "hero_points": pts}).execute()
                    st.success("導入成功")
            except Exception as e: st.error(f"錯誤: {e}")