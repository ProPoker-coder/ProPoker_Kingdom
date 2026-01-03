import streamlit as st
import pandas as pd
import random
import re
import time
import io
import math
import threading
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

# --- 2. 輔助函式 (SQL -> Supabase 轉譯層) ---

# 為了效能，讀取設定檔使用快取 (TTL 30秒)
@st.cache_data(ttl=30) 
def get_all_settings():
    try:
        response = supabase.table("System_Settings").select("*").execute()
        return {item['config_key']: item['config_value'] for item in response.data}
    except: return {}

def get_config(key, default_value):
    settings = get_all_settings()
    return settings.get(key, default_value)

def set_config(key, value):
    try:
        supabase.table("System_Settings").upsert({"config_key": key, "config_value": str(value)}).execute()
        get_all_settings.clear()
    except Exception as e: print(f"Config Error: {e}")

# 獲取玩家資料 (即時)
def get_current_user_data(player_id):
    if 'user_data' not in st.session_state or st.session_state.user_data.get('pf_id') != player_id:
        res = supabase.table("Members").select("*").eq("pf_id", player_id).execute()
        if res.data: st.session_state.user_data = res.data[0]
        else: return None
    return st.session_state.user_data

# 積分與等級計算 (鎖定公式)
def get_rank_v2500(pts):
    limit_c = int(get_config('rank_limit_challenger', "1000"))
    limit_m = int(get_config('rank_limit_master', "500"))
    limit_d = int(get_config('rank_limit_diamond', "200"))
    limit_p = int(get_config('rank_limit_platinum', "80"))
    if pts >= limit_c: return "🏆 菁英"
    elif pts >= limit_m: return "🎖️ 大師"
    elif pts >= limit_d: return "💎 鑽石"
    elif pts >= limit_p: return "⬜ 白金"
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

# VIP 相關
def get_vip_bonus(level):
    return float(get_config(f'vip_bonus_{level}', "0"))

def get_vip_discount(level):
    return float(get_config(f'vip_discount_{level}', "0"))

# 交易日誌
def log_game_transaction(player_id, game, action, amount):
    # 使用背景執行緒避免卡頓
    threading.Thread(target=lambda: supabase.table("Game_Transactions").insert({
        "player_id": player_id, "game_type": game, "action_type": action, 
        "amount": amount, "timestamp": datetime.now().isoformat()
    }).execute()).start()

# XP 更新 (含本地快取與遠端同步)
def update_user_xp(player_id, amount):
    if 'user_data' in st.session_state:
        st.session_state.user_data['xp'] += amount
    # 背景同步 DB
    threading.Thread(target=lambda: _sync_xp(player_id, amount)).start()

def _sync_xp(player_id, amount):
    try:
        # 為了資料一致性，這裡重新抓取並更新，但因為在背景執行，不影響前端速度
        cur = supabase.table("Members").select("xp").eq("pf_id", player_id).execute().data[0]['xp']
        supabase.table("Members").update({"xp": cur + amount}).eq("pf_id", player_id).execute()
    except: pass

# 任務狀態檢查
def check_mission_status(player_id, m_type, criteria, target_val, mission_id):
    now = datetime.now()
    m_res = supabase.table("Missions").select("*").eq("id", mission_id).execute()
    if not m_res.data: return False, False, 0
    m_row = m_res.data[0]
    
    # Time limit check
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
        # Supabase doesn't support COUNT(DISTINCT) directly easily via API in one go without stored procedures, simulating with fetch
        try:
            res = supabase.table("Tournament_Records").select("time").eq("player_id", player_id).gte("time", start_time.isoformat()).execute()
            dates = set(d['time'].split('T')[0] for d in res.data)
            current_val = len(dates); met = current_val >= target_val
        except: pass
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

# --- 3. 旗艦視覺系統 (美工鎖定) ---
def init_flagship_ui():
    m_spd = get_config('marquee_speed', "35")
    m_bg = get_config('welcome_bg_url', "https://img.freepik.com/free-photo/poker-table-dark-atmosphere_23-2151003784.jpg")
    m_title = get_config('welcome_title', "PRO POKER")
    m_subtitle = get_config('welcome_subtitle', "撲 洛 傳 奇 殿 堂")
    
    lb_title_1 = get_config('leaderboard_title_1', "🎖️ 菁英總榜")
    lb_title_2 = get_config('leaderboard_title_2', "🔥 月度戰神")

    m_desc1 = get_config('lobby_desc_1', "♠️ 頂級賽事體驗")
    m_desc2 = get_config('lobby_desc_2', "♥ 公平公正競技")
    m_desc3 = get_config('lobby_desc_3', "♦ 專屬尊榮服務")

    m_mode = get_config('marquee_mode', "custom")
    m_txt = get_config('marquee_text', "撲洛王國營運中，歡迎回歸領地！")
    
    ci_min = int(get_config('checkin_min', "10"))
    ci_max = int(get_config('checkin_max', "500"))

    if m_mode == 'auto':
        try:
            th_xp = int(get_config('marquee_th_xp', "5000"))
            # 這裡為了效率，只抓最新的獎項
            res = supabase.table("Prizes").select("player_id, prize_name, source").order("id", desc=True).limit(20).execute()
            for row in res.data:
                p_name = row['prize_name']
                is_big_win = False
                xp_match = re.search(r'(\d+)\s*XP', str(p_name), re.IGNORECASE)
                if xp_match and int(xp_match.group(1)) >= th_xp: is_big_win = True
                if "大獎" in str(p_name) or "iPhone" in str(p_name): is_big_win = True

                if is_big_win:
                    # 嘗試抓取名字
                    try:
                        mem_res = supabase.table("Members").select("name").eq("pf_id", row['player_id']).execute()
                        p_real_name = mem_res.data[0]['name'] if mem_res.data else row['player_id']
                    except: p_real_name = row['player_id']
                    
                    m_txt = f"🎉 恭喜玩家 【{p_real_name}】 在 {row['source']} 中獲得大獎：{p_name}！ 🔥"
                    break
        except: pass
    
    st.markdown(f"""
        <style>
            :root {{ color-scheme: dark; }}
            html, body, .stApp {{ background-color: #000000 !important; color: #FFFFFF !important; font-family: 'Arial', sans-serif; }}
            
            .stTextInput input, .stNumberInput input, .stSelectbox div, .stTextArea textarea {{ background-color: #1a1a1a !important; color: #FFFFFF !important; border: 1px solid #444 !important; border-radius: 8px !important; }}
            .stButton > button {{ background: linear-gradient(180deg, #333 0%, #111 100%) !important; color: #FFD700 !important; border: 1px solid #FFD700 !important; border-radius: 8px !important; font-weight: bold !important; transition: 0.3s; }}
            .stButton > button:hover {{ background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%) !important; color: #000 !important; transform: scale(1.02); }}
            
            .stTabs [data-baseweb="tab-list"] {{ gap: 5px; background-color: #111; padding: 10px; border-radius: 15px; border: 1px solid #333; }}
            .stTabs [data-baseweb="tab"] {{ background-color: #222; color: #AAA; border-radius: 8px; border: none; }}
            .stTabs [aria-selected="true"] {{ background-color: #FFD700 !important; color: #000 !important; font-weight: bold; }}

            .welcome-wall {{ text-align: center; padding: 60px 20px; background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.9)), url('{m_bg}'); background-size: cover; border-radius: 20px; border: 2px solid #FFD700; margin-bottom: 20px; }}
            .welcome-title {{ font-size: 3.5em; font-weight: 900; color: #FFD700; text-shadow: 0 0 20px rgba(255,215,0,0.8); }}
            .welcome-subtitle {{ font-size: 1.5em; color: #EEE; letter-spacing: 5px; margin-bottom: 30px; }}
            .feature-box {{ display: inline-block; margin: 10px; padding: 10px 20px; background: rgba(0,0,0,0.7); border: 1px solid #555; border-radius: 50px; color: #FFF; }}

            .rank-card {{ background: linear-gradient(135deg, #1a1a1a 0%, #000 100%); border: 2px solid #FFD700; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 0 20px rgba(255, 215, 0, 0.15); height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-card {{ background: linear-gradient(135deg, #000 0%, #222 100%); border: 2px solid #9B30FF; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 0 20px rgba(155, 48, 255, 0.2); height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-badge {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000; padding: 5px 15px; border-radius: 15px; font-weight: 900; display: inline-block; margin-bottom: 15px; box-shadow: 0 0 10px gold; }}
            
            .stats-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
            .stats-item {{ background: rgba(255,255,255,0.05); border: 1px solid #444; padding: 8px; border-radius: 8px; font-size: 0.9em; }}

            .mall-card {{ background: #151515; border: 1px solid #333; border-radius: 12px; padding: 15px; text-align: center; height: 100%; display:flex; flex-direction:column; justify-content:space-between; }}
            .mall-card:hover {{ border-color: #FFD700; transform: translateY(-5px); }}
            .mall-price {{ color: #00FF00; font-weight: bold; font-size: 1.2em; }}
            .vip-price {{ color: #9B30FF; font-weight: bold; font-size: 1.1em; }}
            .mall-img {{ width: 100%; height: 120px; object-fit: contain; margin-bottom: 10px; border-radius: 8px; }}
            
            .lobby-card {{ background: linear-gradient(145deg, #222, #111); border: 1px solid #444; border-radius: 15px; padding: 20px; text-align: center; cursor: pointer; transition: 0.2s; }}
            .lobby-card:hover {{ border-color: #FFD700; transform: scale(1.02); }}
            .lobby-icon {{ font-size: 3em; margin-bottom: 10px; }}
            
            .bacc-zone {{ border: 2px solid; border-radius: 10px; padding: 10px; margin: 5px; min-height: 150px; background-color: rgba(0,0,0,0.3); display:flex; flex-direction:column; align-items:center; justify-content:center; cursor:pointer; transition:0.2s; }}
            .bacc-zone:hover {{ background-color: rgba(255,255,255,0.1); }}
            .bacc-player {{ border-color: #00BFFF; }}
            .bacc-banker {{ border-color: #FF4444; }}
            .bacc-tie {{ border-color: #00FF00; }}
            .bacc-pair {{ border-color: #FFD700; }}
            .bacc-card {{ background-color: #FFF; color: #000; border-radius: 5px; width: 50px; height: 75px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2em; margin: 2px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); }}
            .bacc-card.red {{ color: #D40000; }}
            .bacc-card.black {{ color: #000000; }}
            .bead-plate {{ display: grid; grid-template-columns: repeat(6, 1fr); grid-template-rows: repeat(6, 1fr); gap: 2px; width: 100%; height: 200px; background: #FFF; border: 1px solid #999; overflow-x: auto; margin-bottom: 15px; }}
            .bead {{ width: 25px; height: 25px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; margin: auto; color: white; }}
            .bead-P {{ background: #00BFFF; }}
            .bead-B {{ background: #FF4444; }}
            .bead-T {{ background: #00FF00; color: black; }}

            .roulette-history-bar {{ display: flex; gap: 5px; overflow-x: auto; padding: 10px; background: #000; border-radius: 8px; margin-bottom: 10px; border: 1px solid #333; }}
            .hist-ball {{ min-width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #fff; margin-right: 5px; }}
            .roulette-wheel-anim {{ width: 200px; height: 200px; border-radius: 50%; border: 10px dashed #FFD700; margin: 20px auto; animation: spin-ball 2s cubic-bezier(0.25, 0.1, 0.25, 1); background: radial-gradient(circle, #000 40%, #0d2b12 100%); display: flex; align-items: center; justify-content: center; font-size: 3em; color: #FFF; font-weight: bold; }}
            @keyframes spin-ball {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(3600deg); }} }}
            
            .lm-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; padding: 20px; background: #000; border: 4px solid #FFD700; border-radius: 20px; }}
            .lm-cell {{ background: #222; border: 2px solid #444; border-radius: 10px; padding: 10px; text-align: center; color: #FFF; transition: 0.1s; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
            .lm-active {{ background: #FFF; border-color: #FFD700; color: #000; box-shadow: 0 0 20px #FFD700; transform: scale(1.1); font-weight: bold; }}
            .lm-img {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 5px; }}
            
            .bj-table {{ background-color: #35654d; padding: 30px; border-radius: 20px; border: 8px solid #5c3a21; box-shadow: inset 0 0 50px rgba(0,0,0,0.8); text-align: center; margin-bottom: 20px; }}
            .bj-card {{ background-color: #FFFFFF; color: #000000; border-radius: 6px; display: inline-block; width: 60px; height: 85px; margin: 5px; padding: 5px; font-family: 'Arial', sans-serif; font-weight: bold; font-size: 1.2em; box-shadow: 2px 2px 5px rgba(0,0,0,0.5); vertical-align: middle; line-height: 1.1; }}
            .suit-red {{ color: #D40000 !important; }}
            .suit-black {{ color: #000000 !important; }}

            .lookup-result-box {{ background-color: #000 !important; border: 2px solid #333; border-radius: 10px; padding: 20px; color: #FFF !important; margin-bottom: 20px; }}
            .lookup-label {{ color: #AAA; font-size: 0.9em; }}
            .lookup-value {{ color: #00FF00; font-size: 1.2em; font-weight: bold; }}
            
            .glory-title {{ color: #FFD700; font-size: 2.2em; font-weight: bold; text-align: center; margin-bottom: 20px; border-bottom: 4px solid #FFD700; padding-bottom: 10px; }}
            .lb-rank-card {{ padding: 15px; border-radius: 15px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 10px rgba(0,0,0,0.5); border: 2px solid #FFF; }}
            .lb-rank-1 {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000; box-shadow: 0 0 20px rgba(255,215,0,0.6); transform: scale(1.02); }}
            .lb-rank-2 {{ background: linear-gradient(45deg, #E0E0E0, #B0B0B0); color: #000; box-shadow: 0 0 15px rgba(224,224,224,0.4); }}
            .lb-rank-3 {{ background: linear-gradient(45deg, #CD7F32, #A0522D); color: #FFF; box-shadow: 0 0 10px rgba(205,127,50,0.4); }}
            .lb-rank-norm {{ background: rgba(30,30,30,0.8); border: 1px solid #444; color: #EEE; }}
            .lb-badge {{ font-size: 1.8em; margin-right: 15px; min-width: 40px; text-align: center; }}
            .lb-info {{ display: flex; flex-direction: column; text-align: left; flex-grow: 1; }}
            .lb-name {{ font-weight: 900; font-size: 1.2em; }}
            .lb-id {{ font-size: 0.8em; opacity: 0.8; }}
            .lb-score {{ font-weight: bold; font-size: 1.3em; text-align: right; }}

            .marquee-container {{ background: #1a1a1a; color: #FFD700; padding: 12px 0; overflow: hidden; white-space: nowrap; border-top: 2px solid #FFD700; border-bottom: 2px solid #FFD700; margin-bottom: 25px; }}
            .marquee-text {{ display: inline-block; padding-left: 100%; animation: marquee {m_spd}s linear infinite; font-size: 1.5em; font-weight: bold; }}
            @keyframes marquee {{ 0% {{ transform: translate(0, 0); }} 100% {{ transform: translate(-100%, 0); }} }}
            
            .mission-card {{ background: linear-gradient(90deg, #222 0%, #111 100%); border-left: 5px solid #FFD700; padding: 15px; margin-bottom: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }}
            .mission-title {{ font-size: 1.2em; font-weight: bold; color: #FFF; }}
            .mission-desc {{ font-size: 0.9em; color: #AAA; }}
            .mission-reward {{ color: #00FF00; font-weight: bold; border: 1px solid #00FF00; padding: 5px 10px; border-radius: 15px; }}
            
            .mine-btn {{ width: 100%; aspect-ratio: 1; border-radius: 8px; border: 2px solid #444; background: #222; font-size: 1.5em; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; }}
            .mine-btn:hover {{ border-color: #FFD700; background: #333; }}
            .mine-revealed {{ background: #111; border-color: #666; cursor: default; }}
            .mine-boom {{ background: #500; border-color: #F00; animation: shake 0.5s; }}
            .mine-safe {{ background: #050; border-color: #0F0; }}
            @keyframes shake {{ 0% {{ transform: translate(1px, 1px) rotate(0deg); }} 10% {{ transform: translate(-1px, -2px) rotate(-1deg); }} 20% {{ transform: translate(-3px, 0px) rotate(1deg); }} 30% {{ transform: translate(3px, 2px) rotate(0deg); }} 40% {{ transform: translate(1px, -1px) rotate(1deg); }} 50% {{ transform: translate(-1px, 2px) rotate(-1deg); }} 60% {{ transform: translate(-3px, 1px) rotate(0deg); }} 70% {{ transform: translate(3px, 1px) rotate(-1deg); }} 80% {{ transform: translate(-1px, -1px) rotate(1deg); }} 90% {{ transform: translate(1px, 2px) rotate(0deg); }} 100% {{ transform: translate(1px, -2px) rotate(-1deg); }} }}
        </style>
        <div class="marquee-container"><div class="marquee-text">{m_txt}</div></div>
    """, unsafe_allow_html=True)
    return m_bg, m_title, m_subtitle, m_desc1, m_desc2, m_desc3, lb_title_1, lb_title_2, m_txt, m_spd, m_mode, ci_min, ci_max

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
        res = supabase.table("Members").select("role, password, ban_until").eq("pf_id", p_id_input).execute()
        if res.data: u_chk = res.data[0]
            
    invite_cfg = get_config('reg_invite_code', "888")
    
    if p_id_input and u_chk:
        ban_msg = ""
        if u_chk.get('ban_until'):
            try:
                ban_str = str(u_chk['ban_until']).split('.')[0]
                bt = datetime.strptime(ban_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < bt: ban_msg = f"🚫 帳號封禁中 (至 {u_chk['ban_until']})"
            except: pass
            
        if ban_msg: st.error(ban_msg)
        else:
            login_pw = st.text_input("密碼", type="password", key="sidebar_pw")
            if st.button("登入Pro撲克殿堂"):
                if login_pw == u_chk['password']:
                    st.session_state.player_id = p_id_input; st.session_state.access_level = u_chk['role']; st.query_params["token"] = p_id_input; st.rerun()
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
        if st.button("🚪 退出王國"): st.session_state.player_id = None; st.query_params.clear(); st.rerun()

lb_title_1, lb_title_2, ci_min, ci_max = init_flagship_ui()

if not st.session_state.player_id: st.stop()

# --- 5. 主程式 ---
user_role = st.session_state.access_level
u_row = get_current_user_data(st.session_state.player_id)
t_p = st.tabs(["🪪 排位/VIP", "🎯 任務", "🎮 遊戲大廳", "🛒 商城", "🎒 背包", "🏆 榜單"])

nick_cost = int(get_config('nickname_cost', "500"))

with t_p[0]: # 排位卡
    h_res = supabase.table("Leaderboard").select("hero_points").eq("player_id", st.session_state.player_id).execute()
    h_pts = h_res.data[0]['hero_points'] if h_res.data else 0
    m_res = supabase.table("Monthly_God").select("monthly_points").eq("player_id", st.session_state.player_id).execute()
    m_pts = m_res.data[0]['monthly_points'] if m_res.data else 0
    
    player_rank_title = get_rank_v2500(h_pts)
    vip_lvl = int(u_row.get('vip_level', 0) or 0)
    
    c1, c2 = st.columns(2)
    with c1:
        if 'vip_card_flipped' not in st.session_state: st.session_state.vip_card_flipped = False
        if st.button("💳 翻轉 VIP 卡"): st.session_state.vip_card_flipped = not st.session_state.vip_card_flipped
        
        if not st.session_state.vip_card_flipped:
            st.markdown(f'''<div class="vip-card"><h3>{u_row['name']}</h3><p>ID: {u_row['pf_id']}</p><h2>VIP {vip_lvl}</h2><p>VP: {u_row.get('vip_points', 0):,.0f}</p></div>''', unsafe_allow_html=True)
        else:
            v_desc = get_config('vip_card_desc', 'VIP 點數可用於兌換專屬商品與特權。')
            st.markdown(f'''<div class="vip-card"><h3>VIP 權益說明</h3><p>{v_desc}</p></div>''', unsafe_allow_html=True)

    with c2:
        if 'rank_card_flipped' not in st.session_state: st.session_state.rank_card_flipped = False
        if st.button("🔄 翻轉排位卡"): st.session_state.rank_card_flipped = not st.session_state.rank_card_flipped
        
        if not st.session_state.rank_card_flipped:
            st.markdown(f'''<div class="rank-card"><h3>{player_rank_title}</h3><h1 style="color:#00FF00;">💎 {u_row['xp']:,.0f}</h1><p>積分: {h_pts}</p><p>月積分: {m_pts}</p></div>''', unsafe_allow_html=True)
        else:
            r_desc = get_config('rank_card_desc', '排位與積分規則請見遊戲大廳說明。')
            st.markdown(f'''<div class="rank-card"><h3>系統說明</h3><p>{r_desc}</p></div>''', unsafe_allow_html=True)

    if st.button("🎰 幸運簽到"):
        today = datetime.now().strftime("%Y-%m-%d")
        if str(u_row.get('last_checkin', '')).startswith(today): st.warning("⚠️ 已簽到")
        else:
            rand_factor = random.random() ** 3
            bonus = int(ci_min + (ci_max - ci_min) * rand_factor)
            bonus = int(bonus * (1 + float(get_config(f'vip_bonus_{vip_lvl}', "0"))/100))
            
            update_user_xp(st.session_state.player_id, bonus)
            st.session_state.user_data['last_checkin'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            threading.Thread(target=lambda: supabase.table("Members").update({"last_checkin": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).eq("pf_id", st.session_state.player_id).execute()).start()
            threading.Thread(target=lambda: supabase.table("Prizes").insert({"player_id": st.session_state.player_id, "prize_name": f"{bonus} XP", "status": "自動入帳", "time": datetime.now().isoformat(), "source": "DailyCheckIn"}).execute()).start()
            
            st.success(f"✅ 簽到成功！獲得 {bonus} XP"); st.rerun()

    with st.expander("🔐 安全中心：修改密碼"):
        new_pw = st.text_input("輸入新密碼", type="password", key="reset_pw_box")
        if st.button("⚡ 執行鋼印替換") and new_pw:
            supabase.table("Members").update({"password": new_pw}).eq("pf_id", st.session_state.player_id).execute()
            st.success("✅ 修改成功！")
    with st.expander(f"🏷️ 變更暱稱 ({nick_cost} XP)"):
        new_nick = st.text_input("新暱稱", key="nn")
        if st.button(f"變更"):
            v_res, v_msg = validate_nickname(new_nick)
            if v_res and u_row['xp'] >= nick_cost:
                update_user_xp(st.session_state.player_id, -nick_cost)
                supabase.table("Members").update({"name": new_nick}).eq("pf_id", st.session_state.player_id).execute()
                st.session_state.user_data['name'] = new_nick
                st.success("成功"); st.rerun()
            else: st.error(v_msg if not v_res else "XP 不足")

with t_p[1]: # 任務
    st.subheader("🎯 任務中心")
    missions = supabase.table("Missions").select("*").eq("status", "Active").execute().data
    for m in missions:
        is_met, is_claimed, cur_val = check_mission_status(st.session_state.player_id, m['type'], m['target_criteria'], m['target_value'], m['id'])
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"""<div class="mission-card"><div><div class="mission-title">{m['title']}</div><div class="mission-desc">{m['description']} (進度: {cur_val}/{m['target_value']})</div></div><div class="mission-reward">+{m['reward_xp']} XP</div></div>""", unsafe_allow_html=True)
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
        s_mines = get_config('status_mines', 'ON')
        with c1:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">💣</div><div class="lobby-title">撲洛掃雷</div></div>', unsafe_allow_html=True)
            if s_mines == 'ON': 
                if st.button("進入 掃雷", use_container_width=True): st.session_state.current_game = 'mines'; st.rerun()
            else: st.button("🔧 維修中", disabled=True, use_container_width=True)
        
        s_wheel = get_config('status_wheel', 'ON')
        with c2:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🎡</div><div class="lobby-title">撲洛幸運大轉盤</div></div>', unsafe_allow_html=True)
            if s_wheel == 'ON':
                if st.button("進入 轉盤", use_container_width=True): st.session_state.current_game = 'wheel'; st.rerun()
            else: st.button("🔧 維修中", disabled=True, use_container_width=True)
            
        s_bj = get_config('status_blackjack', 'ON')
        with c3:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">♠️</div><div class="lobby-title">21點 Blackjack</div></div>', unsafe_allow_html=True)
            if s_bj == 'ON':
                if st.button("進入 21點", use_container_width=True): st.session_state.current_game = 'blackjack'; st.rerun()
            else: st.button("🔧 維修中", disabled=True, use_container_width=True)
        
        st.write("")
        c4, c5 = st.columns(2)
        s_bacc = get_config('status_baccarat', 'ON')
        with c4:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🏛️</div><div class="lobby-title">皇家百家樂</div></div>', unsafe_allow_html=True)
            if s_bacc == 'ON':
                if st.button("進入 百家樂", use_container_width=True): st.session_state.current_game = 'baccarat'; st.rerun()
            else: st.button("🔧 維修中", disabled=True, use_container_width=True)
            
        s_roulette = get_config('status_roulette', 'ON')
        with c5:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🔴</div><div class="lobby-title">俄羅斯輪盤</div></div>', unsafe_allow_html=True)
            if s_roulette == 'ON':
                 if st.button("進入 輪盤", use_container_width=True): st.session_state.current_game = 'roulette'; st.rerun()
            else: st.button("🔧 維修中", disabled=True, use_container_width=True)

    else:
        if st.button("⬅️ 返回大廳"): st.session_state.current_game = 'lobby'; st.rerun()

        if st.session_state.current_game == 'mines':
            st.subheader("💣 撲洛掃雷")
            if 'mines_active' not in st.session_state: st.session_state.mines_active = False
            if 'mines_revealed' not in st.session_state or len(st.session_state.mines_revealed) != 25:
                st.session_state.mines_revealed = [False] * 25
                st.session_state.mines_grid = [0] * 25
                st.session_state.mines_active = False
            if 'mines_game_over' not in st.session_state: st.session_state.mines_game_over = False
            
            if not st.session_state.mines_active and not st.session_state.mines_game_over:
                c1, c2 = st.columns(2)
                bet = c1.number_input("投入 XP", 100, 10000, 100)
                mines = c2.slider("地雷數", 1, 24, 3)
                if st.button("🚀 開始"):
                    if u_row['xp'] >= bet:
                        update_user_xp(st.session_state.player_id, -bet)
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
                
                if st.session_state.mines_active:
                    if c_cash.button("💰 結算領錢"):
                        update_user_xp(st.session_state.player_id, cur_win)
                        log_game_transaction(st.session_state.player_id, 'mines', 'WIN', cur_win)
                        st.session_state.mines_active = False
                        st.success(f"贏得 {cur_win} XP"); time.sleep(1); st.rerun()

                cols = st.columns(5)
                for i in range(25):
                    with cols[i%5]:
                        if st.session_state.mines_revealed[i]:
                            if st.session_state.mines_grid[i] == 1: 
                                st.markdown("<div class='mine-btn mine-boom'>💥</div>", unsafe_allow_html=True)
                            else: 
                                st.markdown("<div class='mine-btn mine-safe'>💎</div>", unsafe_allow_html=True)
                        elif st.session_state.mines_game_over and st.session_state.mines_grid[i] == 1:
                             st.markdown("<div class='mine-btn'>💣</div>", unsafe_allow_html=True)
                        else:
                            disabled = st.session_state.mines_game_over
                            if st.button("❓", key=f"m_{i}", disabled=disabled):
                                st.session_state.mines_revealed[i] = True
                                if st.session_state.mines_grid[i] == 1:
                                    st.session_state.mines_active = False
                                    st.session_state.mines_game_over = True
                                    st.error("爆炸了！")
                                st.rerun()
                
                if st.session_state.mines_game_over:
                    if st.button("🔄 再來一局"): 
                        st.session_state.mines_game_over = False
                        st.session_state.mines_active = False
                        st.rerun()

        elif st.session_state.current_game == 'wheel':
             st.subheader("🎡 撲洛幸運大轉盤")
             wheel_cost = int(get_config('min_bet_wheel', "100"))
             st.info(f"消耗: {wheel_cost} XP / 次")
             p_lvl = rank_to_level(player_rank_title)
             
             try:
                 inv_res = supabase.table("Inventory").select("*").gt("stock", 0).in_("target_market", ["Wheel", "Both"]).execute()
                 all_items = pd.DataFrame(inv_res.data)
             except: all_items = pd.DataFrame()
             
             valid_items = []
             if not all_items.empty:
                 for _, item in all_items.iterrows():
                     if rank_to_level(item.get('wheel_min_rank', '無限制')) <= p_lvl: valid_items.append(item.to_dict())
             while len(valid_items) < 8: valid_items.append({"item_name": "銘謝惠顧", "item_value": 0, "img_url": "", "weight": 50})
             display_items = valid_items[:8]
             
             grid_html = "<div class='lm-grid'>"
             for idx, item in enumerate(display_items):
                 active_cls = "lm-active" if st.session_state.get('lm_idx') == idx else ""
                 img_tag = f"<img src='{item['img_url']}' class='lm-img'>" if item.get('img_url') else ""
                 grid_html += f"<div class='lm-cell {active_cls}'>{img_tag}<div>{item['item_name']}</div></div>"
             grid_html += "</div>"
             wheel_placeholder = st.empty(); wheel_placeholder.markdown(grid_html, unsafe_allow_html=True)
             
             if st.button("🚀 啟動"):
                 if u_row['xp'] >= wheel_cost:
                     update_user_xp(st.session_state.player_id, -wheel_cost)
                     
                     weights = [float(i.get('weight', 10)) for i in display_items]
                     win_idx = random.choices(range(len(display_items)), weights=weights, k=1)[0]
                     win_item = display_items[win_idx]
                     for _ in range(2): 
                         for i in range(len(display_items)):
                             st.session_state.lm_idx = i
                             temp_html = "<div class='lm-grid'>"
                             for dx, ditem in enumerate(display_items):
                                 ac = "lm-active" if i == dx else ""
                                 it = f"<img src='{ditem.get('img_url','')}' class='lm-img'>" if ditem.get('img_url') else ""
                                 temp_html += f"<div class='lm-cell {ac}'>{it}<div>{ditem['item_name']}</div></div>"
                             temp_html += "</div>"
                             wheel_placeholder.markdown(temp_html, unsafe_allow_html=True); time.sleep(0.1)
                     st.session_state.lm_idx = win_idx
                     
                     final_html = "<div class='lm-grid'>"
                     for dx, ditem in enumerate(display_items):
                         ac = "lm-active" if win_idx == dx else ""
                         it = f"<img src='{ditem.get('img_url','')}' class='lm-img'>" if ditem.get('img_url') else ""
                         final_html += f"<div class='lm-cell {ac}'>{it}<div>{ditem['item_name']}</div></div>"
                     final_html += "</div>"
                     wheel_placeholder.markdown(final_html, unsafe_allow_html=True)
                     
                     if win_item['item_name'] != "銘謝惠顧":
                         cur_stock = supabase.table("Inventory").select("stock").eq("item_name", win_item['item_name']).execute().data[0]['stock']
                         supabase.table("Inventory").update({"stock": cur_stock - 1}).eq("item_name", win_item['item_name']).execute()
                         supabase.table("Prizes").insert({
                             "player_id": st.session_state.player_id, 
                             "prize_name": win_item['item_name'], 
                             "status": '待兌換', 
                             "time": datetime.now().isoformat(), 
                             "expire_at": "無期限", 
                             "source": 'Wheel'
                         }).execute()
                         st.success(f"恭喜獲得: {win_item['item_name']}"); st.balloons()
                     else: st.info("銘謝惠顧，下次好運！")
                 else: st.error("XP 不足")
        
        elif st.session_state.current_game == 'blackjack':
            st.subheader("♠️ 21點")
            if 'bj_active' not in st.session_state: st.session_state.bj_active = False
            if 'bj_game_over' not in st.session_state: st.session_state.bj_game_over = False

            if not st.session_state.bj_active:
                bet = st.number_input("下注 XP", 100, 10000, 100)
                if st.button("🃏 發牌"):
                    if u_row['xp'] >= bet:
                        update_user_xp(st.session_state.player_id, -bet)
                        st.session_state.bj_active = True
                        st.session_state.bj_game_over = False
                        st.session_state.bj_bet = bet
                        
                        ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
                        suits = ['♠','♥','♦','♣']
                        deck = [(r,s) for r in ranks for s in suits]; random.shuffle(deck)
                        st.session_state.bj_deck = deck
                        st.session_state.bj_p = [deck.pop(), deck.pop()]
                        st.session_state.bj_d = [deck.pop(), deck.pop()]
                        st.rerun()
                    else: st.error("XP 不足")
            else:
                def hand_val(h):
                    v = 0; aces = 0
                    for r, s in h:
                        if isinstance(r, int): v+=r
                        elif r in ['J','Q','K']: v+=10
                        elif r == 'A': v+=11; aces+=1
                    while v > 21 and aces: v-=10; aces-=1
                    return v

                p_val = hand_val(st.session_state.bj_p)
                d_val = hand_val(st.session_state.bj_d) if st.session_state.bj_game_over else hand_val([st.session_state.bj_d[0]])
                
                def render_bj_card(c): return f"<div class='bj-card {'suit-red' if c[1] in ['♥','♦'] else 'suit-black'}'>{c[0]}<br>{c[1]}</div>"
                
                d_html = "".join([render_bj_card(c) for c in st.session_state.bj_d]) if st.session_state.bj_game_over else render_bj_card(st.session_state.bj_d[0]) + "<div class='bj-card'>?</div>"
                p_html = "".join([render_bj_card(c) for c in st.session_state.bj_p])
                
                st.markdown(f"""<div class="bj-table"><h3>莊家: {d_val}</h3><div>{d_html}</div><hr><h3>您: {p_val}</h3><div>{p_html}</div></div>""", unsafe_allow_html=True)
                
                if not st.session_state.bj_game_over:
                    c1, c2 = st.columns(2)
                    if c1.button("🔥 要牌"):
                        st.session_state.bj_p.append(st.session_state.bj_deck.pop())
                        if hand_val(st.session_state.bj_p) > 21:
                             st.session_state.bj_game_over = True
                        st.rerun()
                    if c2.button("✋ 停牌"):
                        while hand_val(st.session_state.bj_d) < 17:
                             st.session_state.bj_d.append(st.session_state.bj_deck.pop())
                        st.session_state.bj_game_over = True
                        st.rerun()
                else:
                    p_final = hand_val(st.session_state.bj_p)
                    d_final = hand_val(st.session_state.bj_d)
                    win = 0; msg = "莊家勝"
                    if p_final > 21: msg = "爆牌！莊家勝"
                    elif d_final > 21: win = 2; msg = "莊家爆牌！您贏了"
                    elif p_final > d_final: win = 2; msg = "恭喜！您贏了"
                    elif p_final == d_final: win = 1; msg = "平局 (Push)"
                    
                    if win > 0:
                         win_amt = int(st.session_state.bj_bet * win)
                         if 'bj_paid_flag' not in st.session_state:
                             update_user_xp(st.session_state.player_id, win_amt)
                             st.session_state.bj_paid_flag = True
                         st.success(f"恭喜！您贏了 {win_amt} XP！"); st.balloons()
                    else: st.error(f"結果: {msg}")
                        
                    if st.button("🔄 再玩一局"):
                        st.session_state.bj_active = False
                        if 'bj_paid_flag' in st.session_state: del st.session_state.bj_paid_flag
                        st.rerun()

        elif st.session_state.current_game == 'baccarat':
            st.subheader("🏛️ 皇家百家樂 (Royal Baccarat)")
            
            if 'bacc_chips' not in st.session_state: st.session_state.bacc_chips = 100
            if 'bacc_bets' not in st.session_state: st.session_state.bacc_bets = {"P":0, "B":0, "T":0, "PP":0, "BP":0}
            
            try:
                b_state = supabase.table("Baccarat_Global").select("*").eq("id", 1).execute().data[0]
                hist_str = b_state['history_string'] if b_state['history_string'] else ""
                hist_list = hist_str.split(',') if hist_str else []
            except: hist_list = []

            st.markdown("#### 📜 牌路")
            bead_html = "<div class='bead-plate'>"
            for h in hist_list:
                if h:
                    val = h[1:] if len(h)>1 else ""
                    type_code = h[0]
                    c = "bead-P" if type_code=='P' else ("bead-B" if type_code=='B' else "bead-T")
                    bead_html += f"<div class='bead {c}'>{val}</div>"
            bead_html += "</div>"
            st.markdown(bead_html, unsafe_allow_html=True)

            if 'bacc_last_res' in st.session_state:
                st.info(st.session_state.bacc_last_res)

            st.write("#### 🪙 選擇籌碼")
            chips = [100, 500, 1000, 5000, 10000]
            chip_cols = st.columns(len(chips))
            for i, c in enumerate(chips):
                with chip_cols[i]:
                    if st.button(f"{chip}", key=f"chip_{chip}"):
                        st.session_state.bacc_chips = chip
            st.info(f"當前選定籌碼: {st.session_state.bacc_chips}")

            c1, c2, c3, c4, c5 = st.columns(5)
            def add_bet(target): st.session_state.bacc_bets[target] += st.session_state.bacc_chips
            
            with c1:
                st.markdown(f"<div class='bacc-zone bacc-player' style='text-align:center;'><h4>🔵 閒 (1:1)</h4><h2>{st.session_state.bacc_bets['P']}</h2></div>", unsafe_allow_html=True)
                st.button("押 閒", key="bet_p", on_click=add_bet, args=("P",), use_container_width=True)
            with c2:
                st.markdown(f"<div class='bacc-zone bacc-banker' style='text-align:center;'><h4>🔴 莊 (1:0.95)</h4><h2>{st.session_state.bacc_bets['B']}</h2></div>", unsafe_allow_html=True)
                st.button("押 莊", key="bet_b", on_click=add_bet, args=("B",), use_container_width=True)
            with c3:
                st.markdown(f"<div class='bacc-zone bacc-tie' style='text-align:center;'><h4>🟢 和 (1:8)</h4><h2>{st.session_state.bacc_bets['T']}</h2></div>", unsafe_allow_html=True)
                st.button("押 和", key="bet_t", on_click=add_bet, args=("T",), use_container_width=True)
            with c4:
                st.markdown(f"<div class='bacc-zone bacc-pair' style='text-align:center;'><h4>🔵 閒對 (1:11)</h4><h2>{st.session_state.bacc_bets['PP']}</h2></div>", unsafe_allow_html=True)
                st.button("押 閒對", key="bet_pp", on_click=add_bet, args=("PP",), use_container_width=True)
            with c5:
                st.markdown(f"<div class='bacc-zone bacc-pair' style='text-align:center;'><h4>🔴 莊對 (1:11)</h4><h2>{st.session_state.bacc_bets['BP']}</h2></div>", unsafe_allow_html=True)
                st.button("押 莊對", key="bet_bp", on_click=add_bet, args=("BP",), use_container_width=True)

            total_bet = sum(st.session_state.bacc_bets.values())
            c_act1, c_act2 = st.columns(2)
            if c_act1.button("🗑️ 清空籌碼"):
                st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                st.rerun()

            if c_act2.button("💰 發牌 (Deal)", type="primary"):
                if total_bet > 0 and u_row['xp'] >= total_bet:
                    update_user_xp(st.session_state.player_id, -total_bet)
                    
                    rtp = float(get_config('rtp_baccarat', "0.95"))
                    deck = [1,2,3,4,5,6,7,8,9,10,11,12,13] * 8; random.shuffle(deck)
                    
                    p_hand = []; b_hand = []
                    winner = "T"
                    
                    for _ in range(10):
                        p_hand = [deck.pop(), deck.pop()]; b_hand = [deck.pop(), deck.pop()]
                        def get_val(h): return sum([0 if c>=10 else c for c in h]) % 10
                        if get_val(p_hand) < 8 and get_val(b_hand) < 8:
                            if get_val(p_hand) <= 5: p_hand.append(deck.pop())
                            if get_val(b_hand) <= 5: b_hand.append(deck.pop()) 
                        
                        p_val = get_val(p_hand); b_val = get_val(b_hand)
                        if p_val > b_val: winner = "P"
                        elif b_val > p_val: winner = "B"
                        else: winner = "T"
                        
                        is_pp = p_hand[0] == p_hand[1]
                        is_bp = b_hand[0] == b_hand[1]

                        pot_win = 0
                        if winner == "P": pot_win += st.session_state.bacc_bets['P'] * 2
                        if winner == "B": pot_win += int(st.session_state.bacc_bets['B'] * 1.95)
                        if winner == "T": pot_win += st.session_state.bacc_bets['T'] * 9
                        if is_pp: pot_win += st.session_state.bacc_bets['PP'] * 12
                        if is_bp: pot_win += st.session_state.bacc_bets['BP'] * 12
                        if winner == "T": pot_win += st.session_state.bacc_bets['P'] + st.session_state.bacc_bets['B']
                        
                        if random.random() > rtp and pot_win > total_bet: continue 
                        else: break
                    
                    if pot_win > 0:
                        update_user_xp(st.session_state.player_id, pot_win)
                        supabase.table("Prizes").insert({
                            "player_id": st.session_state.player_id, 
                            "prize_name": f"{pot_win} XP", 
                            "status": '自動入帳', 
                            "time": datetime.now().isoformat(), 
                            "expire_at": "無期限", 
                            "source": "GameWin-bacc"
                        }).execute()
                    
                    new_entry = f"{winner}{p_val if winner=='P' else b_val}"
                    new_hist = (hist_list + [new_entry])[-60:]
                    
                    supabase.table("Baccarat_Global").update({"hand_count": len(new_hist), "history_string": ",".join(new_hist)}).eq("id", 1).execute()
                    
                    log_game_transaction(st.session_state.player_id, 'baccarat', 'BET', total_bet)
                    if pot_win > 0: log_game_transaction(st.session_state.player_id, 'baccarat', 'WIN', pot_win)

                    ph = st.empty(); bh = st.empty()
                    def render_card(val):
                         s = random.choice(['♠', '♣', '♥', '♦'])
                         c = "red" if s in ['♥', '♦'] else "black"
                         d = {1:'A',11:'J',12:'Q',13:'K'}.get(val, str(val))
                         return f"<div class='bacc-card {c}'>{d}<br>{s}</div>"

                    p_html = ""
                    for card in p_hand:
                        p_html += render_card(card)
                        ph.markdown(f"<div style='text-align:center'><h3>🔵 閒家 ({p_val})</h3><div>{p_html}</div></div>", unsafe_allow_html=True)
                        time.sleep(0.5)
                    
                    b_html = ""
                    for card in b_hand:
                        b_html += render_card(card)
                        bh.markdown(f"<div style='text-align:center'><h3>🔴 莊家 ({b_val})</h3><div>{b_html}</div></div>", unsafe_allow_html=True)
                        time.sleep(0.5)

                    res_msg = f"結果: {winner} ({p_val} vs {b_val})"
                    st.session_state.bacc_last_res = f"上局結果: {res_msg} | 贏得: {pot_win}"
                    
                    if pot_win > total_bet: st.success(f"贏得 {pot_win} XP! {res_msg}"); st.balloons()
                    elif pot_win == total_bet: st.info(f"退回本金 {res_msg}")
                    else: st.error(f"莊家通吃 {res_msg}")
                    
                    st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                    time.sleep(2); st.rerun()

                else: st.error("XP 不足或未下注")

        elif st.session_state.current_game == 'roulette':
            st.subheader("🔴 俄羅斯輪盤 (Roulette)")
            
            try:
                r_state = supabase.table("Roulette_Global").select("*").eq("id", 1).execute().data[0]
                hist_str = r_state['history_string'] if r_state['history_string'] else ""
                hist_list = hist_str.split(',') if hist_str else []
            except: hist_list = []
            
            h_html = "<div class='roulette-history-bar'>"
            for h in hist_list:
                if h:
                    n = int(h)
                    c = "#D40000" if n in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else ("#008000" if n == 0 else "#111")
                    h_html += f"<div class='hist-ball' style='background-color:{c}'>{n}</div>"
            h_html += "</div>"
            st.markdown(h_html, unsafe_allow_html=True)
            
            if 'roulette_last_win' in st.session_state:
                rw = st.session_state.roulette_last_win
                if rw['win'] > 0: st.success(f"🎉 上局開出 {rw['num']}，您贏得 {rw['win']} XP！")
                else: st.error(f"💀 上局開出 {rw['num']}，未中獎。")

            if 'roulette_bets' not in st.session_state: st.session_state.roulette_bets = {} 
            if 'roulette_chips' not in st.session_state: st.session_state.roulette_chips = 100

            st.markdown("##### 🪙 籌碼與操作")
            chips = [100, 500, 1000, 5000, 10000]
            cc = st.columns(len(chips))
            for i, c in enumerate(chips):
                if cc[i].button(f"{c}", key=f"rc_{c}"): st.session_state.roulette_chips = c
            
            total_bet = sum(st.session_state.roulette_bets.values())
            c_act1, c_act2 = st.columns(2)
            c_act1.info(f"💰 總下注: {total_bet} | 籌碼: {st.session_state.roulette_chips}")
            
            if c_act2.button("🚀 旋轉 (SPIN)", type="primary", use_container_width=True):
                if total_bet > 0 and u_row['xp'] >= total_bet:
                    update_user_xp(st.session_state.player_id, -total_bet)
                    
                    rtp = float(get_config('rtp_roulette', "0.95"))
                    
                    potential_loss_nums = []
                    for n in range(37):
                        sim_win = 0
                        red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                        for t, a in st.session_state.roulette_bets.items():
                            is_hit = False
                            if t.isdigit() and int(t) == n: is_hit = True
                            elif t == "紅色" and n in red_nums: is_hit = True
                            elif t == "黑色" and n not in red_nums and n!=0: is_hit = True
                            elif t == "單數" and n!=0 and n%2!=0: is_hit = True
                            elif t == "雙數" and n!=0 and n%2==0: is_hit = True
                            if is_hit:
                                if t.isdigit(): sim_win += a * 36
                                else: sim_win += a * 2
                        if sim_win < total_bet: potential_loss_nums.append(n)
                    
                    if random.random() > rtp and potential_loss_nums:
                        final_num = random.choice(potential_loss_nums) 
                    else:
                        final_num = random.randint(0, 36) 
                    
                    total_win = 0
                    red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                    for t, a in st.session_state.roulette_bets.items():
                        is_win = False
                        if t.isdigit() and int(t) == final_num: is_win = True; mult = 36
                        elif t == "紅色" and final_num in red_nums: is_win = True; mult = 2
                        elif t == "黑色" and final_num not in red_nums and final_num != 0: is_win = True; mult = 2
                        elif t == "單數" and final_num != 0 and final_num % 2 != 0: is_win = True; mult = 2
                        elif t == "雙數" and final_num != 0 and final_num % 2 == 0: is_win = True; mult = 2
                        
                        if is_win: total_win += a * mult
                    
                    if total_win > 0:
                        update_user_xp(st.session_state.player_id, total_win)
                        supabase.table("Prizes").insert({
                            "player_id": st.session_state.player_id, 
                            "prize_name": f"{total_win} XP", 
                            "status": '自動入帳', 
                            "time": datetime.now().isoformat(), 
                            "expire_at": "無期限", 
                            "source": "GameWin-Roulette"
                        }).execute()
                    
                    new_hist_list = [str(final_num)] + hist_list[:39] 
                    new_hist_str = ",".join(new_hist_list)
                    supabase.table("Roulette_Global").update({"history_string": new_hist_str}).eq("id", 1).execute()
                    
                    log_game_transaction(st.session_state.player_id, 'roulette', 'BET', total_bet)
                    if total_win > 0: log_game_transaction(st.session_state.player_id, 'roulette', 'WIN', total_win)
                    
                    st.session_state.roulette_last_win = {'num': final_num, 'win': total_win}
                    
                    placeholder = st.empty()
                    placeholder.markdown('<div class="roulette-wheel-anim">🎲</div>', unsafe_allow_html=True)
                    time.sleep(2)
                    res_c = "#D40000" if final_num in red_nums else ("#008000" if final_num==0 else "#111")
                    placeholder.markdown(f"<div style='text-align:center; font-size:4em; color:{res_c}; font-weight:bold;'>{final_num}</div>", unsafe_allow_html=True)
                    
                    time.sleep(1); st.rerun()

                else: st.error("XP 不足或未下注")

            if st.session_state.roulette_bets:
                with st.expander("📝 查看/編輯下注"):
                    bets_list = list(st.session_state.roulette_bets.keys())
                    c_del1, c_del2 = st.columns([3, 1])
                    del_target = c_del1.selectbox("選擇要刪除的注單", bets_list)
                    if c_del2.button("❌ 刪除"):
                        del st.session_state.roulette_bets[del_target]
                        st.rerun()
                    if st.button("🗑️ 全部清空"):
                        st.session_state.roulette_bets = {}
                        st.rerun()
                    st.table(pd.DataFrame(list(st.session_state.roulette_bets.items()), columns=["下注目標", "金額"]))

            c1, c2, c3 = st.columns([1,12,1])
            with c2:
                if st.button("0 (1:35)", key="rb_0", use_container_width=True): 
                    st.session_state.roulette_bets["0"] = st.session_state.roulette_bets.get("0", 0) + st.session_state.roulette_chips
                
                for row in range(12):
                    rc1, rc2, rc3 = st.columns(3)
                    n1, n2, n3 = row*3+1, row*3+2, row*3+3
                    for n, col in zip([n1,n2,n3], [rc1,rc2,rc3]):
                         color = "🔴" if n in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "⚫"
                         if col.button(f"{color} {n}", key=f"rb_{n}", use_container_width=True):
                             st.session_state.roulette_bets[str(n)] = st.session_state.roulette_bets.get(str(n), 0) + st.session_state.roulette_chips
                
                sb1, sb2 = st.columns(2)
                if sb1.button("🔴 紅色", key="rb_red"): st.session_state.roulette_bets["紅色"] = st.session_state.roulette_bets.get("紅色", 0) + st.session_state.roulette_chips
                if sb2.button("⚫ 黑色", key="rb_black"): st.session_state.roulette_bets["黑色"] = st.session_state.roulette_bets.get("黑色", 0) + st.session_state.roulette_chips
                
                sb3, sb4 = st.columns(2)
                if sb3.button("單數", key="rb_odd"): st.session_state.roulette_bets["Odd"] = st.session_state.roulette_bets.get("Odd", 0) + st.session_state.roulette_chips
                if sb4.button("雙數", key="rb_even"): st.session_state.roulette_bets["Even"] = st.session_state.roulette_bets.get("Even", 0) + st.session_state.roulette_chips

with t_p[3]: # 商城
    st.subheader("🛒 商城")
    try:
        inv_res = supabase.table("Inventory").select("*").gt("stock", 0).in_("target_market", ["Mall", "Both"]).order("item_value", desc=True).execute()
        items = pd.DataFrame(inv_res.data)
    except: items = pd.DataFrame()
    
    if not items.empty:
        ic = st.columns(3)
        for i, r in items.reset_index(drop=True).iterrows():
            with ic[i%3]:
                discount = get_vip_discount(vip_lvl)
                final_xp_price = int(r['mall_price'] * (1 - discount/100.0))
                vip_price_val = r.get('vip_price', 0)
                
                xp_display = f"⚡{final_xp_price:,} XP"
                if discount > 0:
                    xp_display += f" <span style='font-size:0.8em;color:#AAA;text-decoration:line-through;'>({r['mall_price']:,})</span> <span style='font-size:0.8em;color:#FFD700;'>(-{discount}%)</span>"
                
                vp_display = ""
                if vip_price_val > 0:
                    vp_display = f"<div class='vip-price'>💎 {vip_price_val:,} VP</div>"

                limit_txt = f"🔒 需 {r.get('mall_min_rank', '無限制')}" if r.get('mall_min_rank') != '無限制' else "✅ 無限制"
                img_html = f"<img src='{r['img_url']}' class='mall-img'>" if r['img_url'] else ""
                
                st.markdown(f'''<div class="mall-card">{img_html}<div><p>{r['item_name']}</p><p class="mall-price">{xp_display}</p>{vp_display}</div><p style="color:#AAA;font-size:0.8em;margin-top:5px;">{limit_txt}</p></div>''', unsafe_allow_html=True)
                
                p_lvl = rank_to_level(player_rank_title); r_lvl = rank_to_level(r.get('mall_min_rank', '無限制'))
                
                if p_lvl >= r_lvl:
                    c_buy1, c_buy2 = st.columns(2)
                    if c_buy1.button(f"XP 購買", key=f"bxp_{r['item_name']}"):
                        if u_row['xp'] >= final_xp_price:
                            update_user_xp(st.session_state.player_id, -final_xp_price)
                            supabase.table("Inventory").update({"stock": r['stock'] - 1}).eq("item_name", r['item_name']).execute()
                            supabase.table("Prizes").insert({
                                "player_id": st.session_state.player_id, 
                                "prize_name": r['item_name'], 
                                "status": '待兌換', 
                                "time": datetime.now().isoformat(), 
                                "expire_at": "無期限", 
                                "source": '商城購買'
                            }).execute()
                            st.success("購買成功"); st.rerun()
                        else: st.error("XP 不足")
                    
                    if vip_price_val > 0:
                        if c_buy2.button(f"VP 購買", key=f"bvp_{r['item_name']}"):
                             if u_row.get('vip_points', 0) >= vip_price_val:
                                 supabase.table("Members").update({"vip_points": u_row['vip_points'] - vip_price_val}).eq("pf_id", st.session_state.player_id).execute()
                                 supabase.table("Inventory").update({"stock": r['stock'] - 1}).eq("item_name", r['item_name']).execute()
                                 supabase.table("Prizes").insert({
                                     "player_id": st.session_state.player_id, 
                                     "prize_name": r['item_name'], 
                                     "status": '待兌換', 
                                     "time": datetime.now().isoformat(), 
                                     "expire_at": "無期限", 
                                     "source": '商城(VP)'
                                 }).execute()
                                 st.success("VP 購買成功"); st.rerun()
                             else: st.error("VP 不足")
                else: st.button(f"🔒 需 {r['mall_min_rank']}", disabled=True, key=f"lk_{r['item_name']}")

with t_p[4]: # 背包
    st.subheader("🎒 背包")
    try:
        pz_res = supabase.table("Prizes").select("*").eq("player_id", st.session_state.player_id).not_.ilike("source", "GameWin%").order("id", desc=True).execute()
        prizes = pd.DataFrame(pz_res.data)
    except: prizes = pd.DataFrame()
    
    h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 3, 2, 2])
    h1.markdown("**選取**"); h2.markdown("**ID**"); h3.markdown("**來源**"); h4.markdown("**物品**"); h5.markdown("**狀態**"); h6.markdown("**效期**")
    st.write("---")
    sel = []
    if not prizes.empty:
        for _, r in prizes.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 3, 2, 2])
            if c1.checkbox("", key=f"del_{r['id']}"): sel.append(r['id'])
            c2.write(str(r['id'])); c3.write(r['source']); c4.write(r['prize_name']); c5.write(r['status']); c6.write(r.get('expire_at', '無期限'))
    if sel and st.button("🗑️ 刪除選取"):
        for i in sel: supabase.table("Prizes").delete().eq("id", i).execute()
        st.success("已刪除"); st.rerun()

with t_p[5]: # 榜單
    c_lb1, c_lb2 = st.columns(2)
    with c_lb1:
        st.markdown(f"<div class='glory-title'>{lb_title_1}</div>", unsafe_allow_html=True)
        try:
            lb_res = supabase.table("Leaderboard").select("player_id, hero_points").neq("player_id", "330999").order("hero_points", desc=True).limit(20).execute()
            lb_data = lb_res.data
        except: lb_data = []
        
        if lb_data:
            for i, row in enumerate(lb_data):
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                curr_rank = get_rank_v2500(row['hero_points'])
                
                p_name = row['player_id']
                try:
                    mem_q = supabase.table("Members").select("name").eq("pf_id", row['player_id']).execute()
                    if mem_q.data: p_name = mem_q.data[0]['name']
                except: pass
                
                st.markdown(f"""<div class="lb-rank-card {style_class}"><div class="lb-badge">{badge}</div><div class="lb-info"><div class="lb-name">{p_name} <span style="font-size:0.8em;color:#DDD;">({curr_rank})</span></div><div class="lb-id">{row['player_id']}</div></div><div class="lb-score">{row['hero_points']}</div></div>""", unsafe_allow_html=True)
        else: st.info("暫無資料")

    with c_lb2:
        st.markdown(f"<div class='glory-title'>{lb_title_2}</div>", unsafe_allow_html=True)
        try:
            mg_res = supabase.table("Monthly_God").select("player_id, monthly_points").neq("player_id", "330999").order("monthly_points", desc=True).limit(20).execute()
            mg_data = mg_res.data
        except: mg_data = []
        
        if mg_data:
            for i, row in enumerate(mg_data):
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                
                p_name = row['player_id']
                try:
                    mem_q = supabase.table("Members").select("name").eq("pf_id", row['player_id']).execute()
                    if mem_q.data: p_name = mem_q.data[0]['name']
                except: pass

                st.markdown(f"""<div class="lb-rank-card {style_class}"><div class="lb-badge">{badge}</div><div class="lb-info"><div class="lb-name">{p_name}</div><div class="lb-id">{row['player_id']}</div></div><div class="lb-score">{row['monthly_points']}</div></div>""", unsafe_allow_html=True)
        else: st.info("暫無資料")

# --- 5. 指揮部 (Admin) ---
if st.session_state.access_level in ["老闆", "店長", "員工"]:
    st.write("---"); st.header("⚙️ 指揮部")
    
    tabs = st.tabs(["💰 櫃台與物資", "👥 人員與空投", "📊 賽事與數據", "🛠️ 系統與維護"])
    with tabs[0]: 
        st.subheader("🛂 櫃台核銷")
        target = st.text_input("玩家 ID")
        if target:
            try:
                pend_res = supabase.table("Prizes").select("id, prize_name").eq("player_id", target).eq("status", "待兌換").execute()
                prizes_data = pend_res.data
            except: prizes_data = []
            
            display_data = []
            if prizes_data:
                p_names = list(set([p['prize_name'] for p in prizes_data]))
                if p_names:
                    try:
                        inv_res = supabase.table("Inventory").select("item_name, item_value, vip_card_level, vip_card_hours").in_("item_name", p_names).execute()
                        inv_map = {i['item_name']: i for i in inv_res.data}
                    except: inv_map = {}
                else: inv_map = {}
                
                for p in prizes_data:
                    p_name = p['prize_name']
                    inv_info = inv_map.get(p_name, {}) 
                    display_data.append({
                        "id": p['id'], 
                        "prize_name": p_name, 
                        "item_value": inv_info.get('item_value', 0),
                        "vip_level": inv_info.get('vip_card_level', 0),
                        "vip_hours": inv_info.get('vip_card_hours', 0)
                    })
            
            if display_data:
                df_pend = pd.DataFrame(display_data)
                st.table(df_pend)
                redeem_id = st.selectbox("選擇核銷項目 ID", df_pend['id'].tolist())
                max_val = int(get_config('max_redeem_val', "1000000"))
                
                selected_item = next((x for x in display_data if x['id'] == redeem_id), None)
                
                if user_role != "老闆" and selected_item['item_value'] > max_val:
                    st.error(f"❌ 此物品價值 ({selected_item['item_value']}) 超過權限，請聯繫老闆。")
                else:
                    if st.button("確認核銷 (自動入帳)"):
                        if selected_item['vip_hours'] > 0:
                            mem = supabase.table("Members").select("vip_level, vip_expiry").eq("pf_id", target).execute().data[0]
                            c_lvl = mem.get('vip_level', 0)
                            c_exp = mem.get('vip_expiry')
                            now = datetime.now(); start_time = now
                            if c_lvl == selected_item['vip_level'] and c_exp:
                                try:
                                    exp_dt = datetime.strptime(str(c_exp).split('.')[0], "%Y-%m-%d %H:%M:%S")
                                    if exp_dt > now: start_time = exp_dt
                                except: pass
                            new_exp = (start_time + timedelta(hours=int(selected_item['vip_hours']))).strftime("%Y-%m-%d %H:%M:%S")
                            supabase.table("Members").update({"vip_level": int(selected_item['vip_level']), "vip_expiry": new_exp}).eq("pf_id", target).execute()
                            st.toast(f"💎 VIP 權益已開通至 {new_exp}")

                        xp_match = re.search(r'(\d+)\s*XP', str(selected_item['prize_name']), re.IGNORECASE)
                        if xp_match:
                            add_xp = int(xp_match.group(1))
                            update_user_xp(target, add_xp)
                            st.toast(f"💰 已自動儲值 {add_xp} XP")
                        
                        supabase.table("Prizes").update({"status": '已核銷'}).eq("id", redeem_id).execute()
                        supabase.table("Staff_Logs").insert({"staff_id": st.session_state.player_id, "player_id": target, "prize_name": selected_item['prize_name'], "time": datetime.now().isoformat()}).execute()
                        st.success("核銷作業完成！"); time.sleep(1); st.rerun()
            else: st.info("該玩家無待核銷物品")
            
            if user_role == "老闆":
                st.write("---"); st.subheader("💰 人工充值 (老闆限定)")
                xp_add = st.number_input("充值 XP", step=100)
                if st.button("執行充值"):
                    update_user_xp(target, xp_add)
                    st.success("已充值")
            
            st.write("---"); st.subheader("📜 櫃台核銷歷史查詢")
            hd1 = st.date_input("起始日期")
            hd2 = st.date_input("結束日期")
            if st.button("查詢歷史紀錄"):
                 hq_start = hd1.strftime("%Y-%m-%d 00:00:00"); hq_end = hd2.strftime("%Y-%m-%d 23:59:59")
                 try:
                     logs_res = supabase.table("Staff_Logs").select("*").gte("time", hq_start).lte("time", hq_end).order("time", desc=True).execute()
                     st.dataframe(pd.DataFrame(logs_res.data))
                 except: st.error("查詢失敗")
                 
                 if user_role == "老闆":
                     if st.button("⚠️ 刪除此區間紀錄 (老闆權限)"):
                         supabase.table("Staff_Logs").delete().gte("time", hq_start).lte("time", hq_end).execute()
                         st.warning("紀錄已刪除")

        st.write("---")
        with st.expander("📦 商品上架與管理"):
            st.write("#### 🛒 上架新商品")
            c1, c2 = st.columns(2)
            n = c1.text_input("商品名稱")
            s = c2.number_input("庫存", 0, 9999, 10)
            
            c3, c4, c5 = st.columns(3)
            v = c3.number_input("顯示市價 (僅參考)", 0)
            w = c4.number_input("轉盤權重 (越大越容易中)", 0.0, 1000.0, 10.0)
            mp = c5.number_input("商城售價 (XP)", 0)
            
            st.markdown("---")
            is_vip = st.checkbox("👑 此商品為 VIP 權益卡")
            v_lvl = 0; v_hrs = 0
            if is_vip:
                c_v1, c_v2 = st.columns(2)
                v_lvl = c_v1.selectbox("設定 VIP 等級", [1, 2, 3, 4], format_func=lambda x: {1:"銅牌",2:"銀牌",3:"黃金",4:"鑽石"}[x])
                v_hrs = c_v2.number_input("VIP 有效時數 (小時)", 1, 8760, 720)
            
            st.markdown("---")
            img = st.text_input("圖片 URL (可留空)")
            r_min = st.selectbox("購買排位限制", ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"])
            vp_price = st.number_input("VP 點數售價 (0 = 不開放 VP 購買)", 0)
            target_m = st.selectbox("上架位置", ["Both", "Mall", "Wheel"])
            
            if st.button("確認上架商品"):
                if n:
                    supabase.table("Inventory").insert({
                        "item_name": n, "stock": s, "item_value": v, "weight": w, "target_market": target_m,
                        "mall_price": mp, "vip_card_level": v_lvl, "vip_card_hours": v_hrs,
                        "img_url": img, "mall_min_rank": r_min, "vip_price": vp_price
                    }).execute()
                    st.success(f"✅ 商品 {n} 上架成功！"); time.sleep(1); st.rerun()
                else: st.error("名稱不可為空")
            
            st.markdown("---")
            st.write("📋 **架上商品列表 (可編輯/刪除)**")
            try:
                inv_res = supabase.table("Inventory").select("*").execute()
                inv_data = inv_res.data
            except: inv_data = []
            
            if inv_data:
                for mm in inv_data:
                    with st.expander(f"{mm['item_name']} (庫存: {mm['stock']})"):
                        c1, c2, c3, c4 = st.columns(4)
                        new_p = c1.number_input(f"XP售價", value=int(mm['mall_price']), key=f"mm_p_{mm['item_name']}")
                        new_vp = c2.number_input(f"VP售價", value=int(mm.get('vip_price', 0)), key=f"mm_vp_{mm['item_name']}")
                        new_s = c3.number_input(f"庫存", value=mm['stock'], key=f"mm_s_{mm['item_name']}")
                        
                        r_opts = ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"]
                        curr_r = mm.get('mall_min_rank', '無限制')
                        if curr_r not in r_opts: curr_r = "無限制"
                        r_idx = r_opts.index(curr_r)
                        
                        new_r = c4.selectbox(f"限制", r_opts, index=r_idx, key=f"mm_r_{mm['item_name']}")
                        
                        c5, c6, c7 = st.columns([2, 1, 1])
                        new_u = c5.text_input("圖片", value=mm['img_url'], key=f"mm_u_{mm['item_name']}")
                        new_st = c6.selectbox("狀態", ["上架中", "下架中"], index=0 if mm.get('status')=='上架中' else 1, key=f"mm_st_{mm['item_name']}")
                        if c7.button(f"💾 保存", key=f"mm_up_{mm['item_name']}"):
                            supabase.table("Inventory").update({
                                "mall_price": new_p, "vip_price": new_vp, "stock": new_s, 
                                "mall_min_rank": new_r, "img_url": new_u, "status": new_st
                            }).eq("item_name", mm['item_name']).execute()
                            st.success("已更新"); st.rerun()
                        if st.button("刪除商品", key=f"mm_del_{mm['item_name']}"):
                             supabase.table("Inventory").delete().eq("item_name", mm['item_name']).execute()
                             st.success("Deleted"); st.rerun()

    with tabs[1]: # 人員與空投
        st.subheader("🔍 查閱與管理")
        q = st.text_input("查詢玩家 ID", key="query_lookup_id_2")
        if q:
            try:
                mem_res = supabase.table("Members").select("*").eq("pf_id", q).execute()
                mem_data = mem_res.data
            except: mem_data = []
            
            if mem_data:
                mem = mem_data[0]
                st.markdown(f"""
                <div class="lookup-result-box">
                    <h3>👤 {mem['name']} (ID: {q})</h3>
                    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr;">
                        <div><span class="lookup-label">XP 餘額</span><br><span class="lookup-value">{mem['xp']:,.0f}</span></div>
                        <div><span class="lookup-label">VIP 點數</span><br><span class="lookup-value">{mem['vip_points']:,.0f}</span></div>
                        <div><span class="lookup-label">角色權限</span><br><span style="color:#FFD700;">{mem['role']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Check contribution
                try:
                    tr_res = supabase.table("Tournament_Records").select("actual_fee").eq("player_id", q).execute()
                    total_contribution = sum(r['actual_fee'] for r in tr_res.data)
                except: total_contribution = 0
                st.markdown(f"**生涯總貢獻 (淨利): {total_contribution:,}**")

                if user_role == "老闆":
                    with st.expander("🚫 封禁管理"):
                        if st.button("❌ 物理刪除玩家"):
                            supabase.table("Members").delete().eq("pf_id", q).execute()
                            supabase.table("Prizes").delete().eq("player_id", q).execute()
                            supabase.table("Leaderboard").delete().eq("player_id", q).execute()
                            st.error("已刪除"); st.rerun()
                            
                    with st.expander("👮 懲處：扣除玩家 XP"):
                         deduct_xp = st.number_input("扣除數量", min_value=1, value=100, key="deduct_xp_val_2")
                         if st.button("執行扣除", key="btn_deduct_xp_2"):
                             update_user_xp(q, -deduct_xp)
                             st.success("已扣除"); st.rerun()

                with st.expander("🎰 近 20 場遊戲紀錄"):
                    try:
                        gw = supabase.table("Prizes").select("source, prize_name, time").eq("player_id", q).ilike("source", "GameWin%").order("id", desc=True).limit(20).execute()
                        st.table(pd.DataFrame(gw.data))
                    except: pass
                
                with st.expander("🎒 背包庫存"):
                    try:
                        bp = supabase.table("Prizes").select("prize_name, status, expire_at").eq("player_id", q).eq("status", "待兌換").order("id", desc=True).execute()
                        st.table(pd.DataFrame(bp.data))
                    except: pass

            else: st.error("無此人")

        st.write("---")
        st.subheader("🚀 物資空投")
        target_group = st.selectbox("發送對象", ["單一玩家 ID", "全體玩家", "🏆 菁英", "🎖️ 大師", "💎 鑽石", "⬜ 白金", "🥈 白銀", "VIP 1 (銅)", "VIP 2 (銀)", "VIP 3 (金)", "VIP 4 (鑽)"])
        
        target_ids = []
        if target_group == "單一玩家 ID":
            tid = st.text_input("輸入玩家 ID")
            if tid: target_ids = [tid]
        elif target_group == "全體玩家":
            try:
                res = supabase.table("Members").select("pf_id").execute()
                target_ids = [r['pf_id'] for r in res.data]
            except: pass
        else:
            if "VIP" in target_group:
                lvl = int(target_group.split(" ")[2])
                try:
                    res = supabase.table("Members").select("pf_id").eq("vip_level", lvl).execute()
                    target_ids = [r['pf_id'] for r in res.data]
                except: pass
            
        st.info(f"預計發送對象人數: {len(target_ids)} 人")
        
        c_xp, c_vp, c_it = st.columns(3)
        xp = c_xp.number_input("XP 點數", 0)
        vp = c_vp.number_input("VIP 點數", 0)
        
        try:
            inv_list = supabase.table("Inventory").select("item_name").execute()
            it_opts = ["無"] + [i['item_name'] for i in inv_list.data]
        except: it_opts = ["無"]
        it = c_it.selectbox("禮物 (庫存)", it_opts)
        
        if st.button("確認空投"):
            if not target_ids: st.error("無目標")
            else:
                for t in target_ids:
                    if xp or vp:
                        update_user_xp(t, xp)
                        threading.Thread(target=lambda: supabase.table("Members").update({"vip_points": supabase.table("Members").select("vip_points").eq("pf_id", t).execute().data[0]['vip_points'] + vp}).eq("pf_id", t).execute()).start()
                    
                    if it != "無":
                         # Async prize insert
                         threading.Thread(target=lambda: supabase.table("Prizes").insert({"player_id": t, "prize_name": it, "status": '待兌換', "time": datetime.now().isoformat(), "expire_at": "無期限", "source": '老闆空投'}).execute()).start()
                st.success("空投完成")

    with tabs[2]: # 賽事與數據
        st.subheader("📁 賽事精算導入 (已修復 XP 公式)")
        
        st.info("""
        **🧮 積分計算公式 (雙榜同步)：**
        `積分 = 底分 + (底分 * (1/名次) * 1.5) + (底分 * 重購次數)`
        *(註：買入<3000底分100，買入>=3000底分200)*

        **💰 XP 獎勵公式 (全額回饋)：**
        `XP = 實際手續費`
        *(不再扣除 10%，不含獎金)*
        """)
        
        up = st.file_uploader("上傳 CSV / Excel")
        if up and st.button("執行精算"):
            try:
                fn = up.name; buy = 1000 
                match = re.search(r'(\d+)', fn)
                if match: buy = int(match.group(1))
                
                if fn.endswith('.csv'):
                    try: df = pd.read_csv(up, encoding='utf-8-sig')
                    except: 
                        up.seek(0)
                        df = pd.read_csv(up, encoding='big5')
                else: df = pd.read_excel(up)
                
                df.columns = df.columns.str.strip()
                
                try:
                    chk = supabase.table("Import_History").select("filename").eq("filename", fn).execute()
                    if chk.data:
                        st.error(f"❌ 檔案 {fn} 已被匯入過！"); st.stop()
                except: pass
                
                # 積分矩陣 (還原舊版邏輯)
                matrix = {
                    1200: (200, 0.75, [2, 1.5, 1]),
                    3400: (400, 1.5, [5, 4, 3]),
                    6600: (600, 2.0, [10, 8, 6]),
                    11000: (1000, 3.0, [20, 15, 10]),
                    21500: (1500, 5.0, [40, 30, 20])
                }
                base, p_mult, bonuses = matrix.get(buy, (100, 1.0, [1, 1, 1]))
                if buy >= 3000 and buy not in matrix: base = 200 
                
                for _, r in df.iterrows():
                    pid = str(r['ID']); raw_name = str(r['Nickname']); name = raw_name[:10]
                    # Ensure Member exists
                    try:
                        mem = supabase.table("Members").select("pf_id").eq("pf_id", pid).execute()
                        if not mem.data:
                            supabase.table("Members").insert({"pf_id": pid, "name": name, "role": "玩家", "xp": 0}).execute()
                    except: pass
                    
                    rank = int(r['Rank'])
                    re_e = int(r.get('Re-Entries', 0))
                    payout = int(r.get('Payout', 0))
                    ents = re_e + 1
                    
                    # 抓取抵用卷折扣
                    remark = str(r.get('Remark', '')) if pd.notna(r.get('Remark')) else ''
                    discounts = sum([int(d) for d in re.findall(r'(\d+)抵用卷', remark)])

                    # 計算實際手續費
                    total_service_fee_gross = base * ents
                    actual_fee = max(0, total_service_fee_gross - discounts)
                    
                    # [修正] XP = 實際手續費 (完全不含獎金，100% 回饋)
                    xp_reward = actual_fee
                    update_user_xp(pid, xp_reward)
                    
                    # 計算積分
                    rank_bonus = bonuses[rank-1] if rank <= 3 else 0
                    pts = int(ents * p_mult) + rank_bonus
                    
                    # 雙榜同步更新
                    try:
                        cur_h = supabase.table("Leaderboard").select("hero_points").eq("player_id", pid).execute().data[0]['hero_points']
                        supabase.table("Leaderboard").update({"hero_points": cur_h + pts}).eq("player_id", pid).execute()
                    except:
                        supabase.table("Leaderboard").insert({"player_id": pid, "hero_points": pts}).execute()
                        
                    try:
                        cur_m = supabase.table("Monthly_God").select("monthly_points").eq("player_id", pid).execute().data[0]['monthly_points']
                        supabase.table("Monthly_God").update({"monthly_points": cur_m + pts}).eq("player_id", pid).execute()
                    except:
                        supabase.table("Monthly_God").insert({"player_id": pid, "monthly_points": pts}).execute()
                    
                    # Log
                    supabase.table("Tournament_Records").insert({
                        "player_id": pid, "buy_in": buy, "rank": rank, "re_entries": re_e, "payout": payout, "filename": fn,
                        "actual_fee": actual_fee,
                        "time": datetime.now().isoformat()
                    }).execute()
                
                supabase.table("Import_History").insert({"filename": fn, "import_time": datetime.now().isoformat()}).execute()
                st.balloons(); st.success(f"✅ 成功匯入 {fn}")

            except Exception as e: st.error(f"匯入失敗: {e}")

    with tabs[3]: # 系統設定
        if user_role == "老闆":
            st.subheader("⚙️ 遊戲參數設定")
            c1, c2, c3 = st.columns(3)
            c1.number_input("輪盤 RTP", value=float(get_config('rtp_roulette', 0.95)), key='rtp_r')
            c2.number_input("百家樂 RTP", value=float(get_config('rtp_baccarat', 0.95)), key='rtp_b')
            c3.number_input("21點 RTP", value=float(get_config('rtp_blackjack', 0.95)), key='rtp_bj')
            
            if st.button("保存遊戲參數"):
                set_config('rtp_roulette', st.session_state.rtp_r)
                set_config('rtp_baccarat', st.session_state.rtp_b)
                set_config('rtp_blackjack', st.session_state.rtp_bj)
                st.success("已更新")

            st.write("---")
            # [修復] 每日簽到設定
            st.subheader("📅 每日簽到設定")
            c_min, c_max = st.columns(2)
            new_cmin = c_min.number_input("最小獎勵", value=int(get_config('checkin_min', 10)))
            new_cmax = c_max.number_input("最大獎勵", value=int(get_config('checkin_max', 500)))
            if st.button("保存簽到設定"):
                set_config('checkin_min', new_cmin)
                set_config('checkin_max', new_cmax)
                st.success("已更新")

            st.write("---")
            st.subheader("🎨 卡片與排位設定")
            c1, c2, c3, c4 = st.columns(4)
            rc = c1.number_input("菁英分數", value=int(get_config('rank_limit_challenger', 1000)))
            rm = c2.number_input("大師分數", value=int(get_config('rank_limit_master', 500)))
            rd = c3.number_input("鑽石分數", value=int(get_config('rank_limit_diamond', 200)))
            rp = c4.number_input("白金分數", value=int(get_config('rank_limit_platinum', 80)))
            
            rank_desc = st.text_area("排位卡背面說明", value=get_config('rank_card_desc', '排位與積分規則說明...'))
            vip_desc = st.text_area("VIP 卡背面說明", value=get_config('vip_card_desc', 'VIP 權益說明...'))
            
            if st.button("保存排位與卡片設定"):
                set_config('rank_limit_challenger', rc)
                set_config('rank_limit_master', rm)
                set_config('rank_limit_diamond', rd)
                set_config('rank_limit_platinum', rp)
                set_config('rank_card_desc', rank_desc)
                set_config('vip_card_desc', vip_desc)
                st.success("設定已更新")
                
            st.write("---")
            # [修復] 賽季結算與重置
            st.subheader("🗑️ 賽季結算與重置")
            scheme = st.selectbox("結算方案", ["方案A: 全扣150", "方案B: 扣10%", "軟重置: 保留40%"])
            if st.button("執行賽季結算"):
                try:
                    all_lb = supabase.table("Leaderboard").select("*").neq("player_id", "330999").execute().data
                    for p in all_lb:
                        old_pts = p['hero_points']
                        new_pts = old_pts
                        if "方案A" in scheme: new_pts = max(0, old_pts - 150)
                        elif "方案B" in scheme: new_pts = int(old_pts * 0.9)
                        elif "軟重置" in scheme: new_pts = int(old_pts * 0.4)
                        
                        supabase.table("Leaderboard").update({"hero_points": new_pts}).eq("player_id", p['player_id']).execute()
                    st.success("賽季結算完成")
                except: st.error("結算失敗")

            st.write("---")
            st.markdown("### ⚖️ 上帝之手 (手動調整)")
            c1, c2, c3, c4 = st.columns(4)
            god_pid = c1.text_input("玩家 ID", key="god_pid")
            god_pts = c2.number_input("增減積分 (+/-)", value=0)
            
            if c3.button("執行調整"):
                try:
                    # 雙榜調整
                    cur_h = supabase.table("Leaderboard").select("hero_points").eq("player_id", god_pid).execute().data[0]['hero_points']
                    supabase.table("Leaderboard").update({"hero_points": cur_h + god_pts}).eq("player_id", god_pid).execute()
                    
                    cur_m = supabase.table("Monthly_God").select("monthly_points").eq("player_id", god_pid).execute().data[0]['monthly_points']
                    supabase.table("Monthly_God").update({"monthly_points": cur_m + god_pts}).eq("player_id", god_pid).execute()
                    st.success("已調整")
                except: st.error("玩家不存在或無積分紀錄")
            
            if c4.button("💥 歸零重置"):
                try:
                    supabase.table("Leaderboard").update({"hero_points": 0}).eq("player_id", god_pid).execute()
                    supabase.table("Monthly_God").update({"monthly_points": 0}).eq("player_id", god_pid).execute()
                    st.success("已歸零")
                except: st.error("歸零失敗")

        st.write("---")
        # [修復] 任務新增功能
        st.subheader("📜 任務管理")
        with st.expander("➕ 新增任務", expanded=False):
            with st.form("add_m_form"):
                t = st.text_input("標題")
                d = st.text_input("描述")
                xp = st.number_input("獎勵 XP", 100)
                tp = st.selectbox("類型", ["Daily", "Weekly", "Monthly"])
                cr = st.selectbox("條件", ["daily_checkin", "consecutive_checkin", "daily_win"])
                val = st.number_input("目標值", 1)
                
                inv_items = ["無"]
                try: 
                    inv = supabase.table("Inventory").select("item_name").execute().data
                    inv_items += [i['item_name'] for i in inv]
                except: pass
                it = st.selectbox("獎勵物品", inv_items)
                
                if st.form_submit_button("新增"):
                    item_val = None if it == "無" else it
                    supabase.table("Missions").insert({
                        "title": t, "description": d, "reward_xp": xp, "type": tp, 
                        "target_criteria": cr, "target_value": val, "status": "Active", "reward_item": item_val
                    }).execute()
                    st.success("任務已新增")

        # [新增] 老闆一鍵重置
        if user_role == "老闆":
            st.write("---")
            st.markdown("### 🧨 危險區域")
            if st.button("🔥 刪除所有玩家數據 (保留老闆)", type="primary"):
                supabase.table("Prizes").delete().neq("player_id", "330999").execute()
                supabase.table("Game_Transactions").delete().neq("player_id", "330999").execute()
                supabase.table("Leaderboard").delete().neq("player_id", "330999").execute()
                supabase.table("Monthly_God").delete().neq("player_id", "330999").execute()
                supabase.table("Mission_Logs").delete().neq("player_id", "330999").execute()
                supabase.table("Members").delete().neq("pf_id", "330999").execute()
                st.toast("💥 所有測試數據已清除！")