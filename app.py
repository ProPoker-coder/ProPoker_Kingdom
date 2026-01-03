import streamlit as st
import pandas as pd
import random
import re
import time
import math
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
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key)
        else:
            st.error("❌ 找不到 secrets 設定。請在 .streamlit/secrets.toml 設定 [supabase]")
            st.stop()
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        st.stop()

supabase: Client = init_connection()

# --- 2. 輔助函式 (SQL -> Supabase 轉換) ---

def get_config(key, default_value):
    """從 System_Settings 讀取設定"""
    try:
        response = supabase.table("System_Settings").select("config_value").eq("config_key", key).execute()
        if response.data:
            return response.data[0]['config_value']
        return default_value
    except:
        return default_value

def set_config(key, value):
    """寫入設定"""
    try:
        supabase.table("System_Settings").upsert({"config_key": key, "config_value": str(value)}).execute()
    except Exception as e:
        print(f"Config Error: {e}")

def init_flagship_ui():
    """讀取雲端設定並渲染介面"""
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

    # 自動跑馬燈邏輯
    if m_mode == 'auto':
        try:
            th_xp = int(get_config('marquee_th_xp', "5000"))
            res = supabase.table("Prizes").select("player_id, prize_name, source").order("id", desc=True).limit(20).execute()
            
            found_news = False
            for row in res.data:
                p_name = row['prize_name']
                is_big_win = False
                xp_match = re.search(r'(\d+)\s*XP', str(p_name), re.IGNORECASE)
                if xp_match and int(xp_match.group(1)) >= th_xp: is_big_win = True
                if "大獎" in str(p_name) or "iPhone" in str(p_name): is_big_win = True

                if is_big_win:
                    mem_res = supabase.table("Members").select("name").eq("pf_id", row['player_id']).execute()
                    p_real_name = mem_res.data[0]['name'] if mem_res.data else row['player_id']
                    m_txt = f"🎉 恭喜玩家 【{p_real_name}】 在 {row['source']} 中獲得大獎：{p_name}！ 🔥"
                    found_news = True
                    break
            if not found_news: m_txt = "💎 撲洛王國大獎頻傳，下一個幸運兒就是你！"
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
            .game-table-area {{ background-color: #0d2b12; border: 8px solid #3e2723; border-radius: 30px; padding: 20px; box-shadow: inset 0 0 50px #000; margin-bottom: 20px; }}
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
    if "白銀" in rank_str: return 1
    return 0

def validate_nickname(nickname):
    if not nickname or not nickname.strip(): return False, "暱稱不可為空"
    is_ascii = all(ord(c) < 128 for c in nickname)
    if is_ascii:
        if len(nickname) > 10: return False, "英文暱稱不可超過 10 個字母"
    else:
        if len(nickname) > 6: return False, "中文暱稱不可超過 6 個字"
    return True, "OK"

def get_vip_bonus(level):
    if level <= 0: return 0.0
    return float(get_config(f'vip_bonus_{level}', "0"))

def get_vip_discount(level):
    if level <= 0: return 0.0
    return float(get_config(f'vip_discount_{level}', "0"))

def log_game_transaction(player_id, game, action, amount):
    supabase.table("Game_Transactions").insert({
        "player_id": player_id,
        "game_type": game,
        "action_type": action,
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }).execute()

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

m_bg, m_title, m_subtitle, m_desc1, m_desc2, m_desc3, lb_title_1, lb_title_2, m_txt, m_spd, m_mode, ci_min, ci_max = init_flagship_ui()

# --- Auth ---
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
        if res.data:
            u_chk = res.data[0]
            
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
            st.info("⚠️ 首次註冊：系統將自動檢查是否為比賽匯入的 ID。")
            rn = st.text_input("暱稱"); rpw = st.text_input("密碼", type="password"); ri = st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                v_res, v_msg = validate_nickname(rn)
                if v_res:
                    # Check exist with no pw
                    exist = supabase.table("Members").select("*").eq("pf_id", p_id_input).execute()
                    if exist.data and (not exist.data[0]['password']):
                         supabase.table("Members").update({"name": rn, "password": rpw, "role": "玩家", "join_date": datetime.now().strftime("%Y-%m-%d")}).eq("pf_id", p_id_input).execute()
                         st.success("✅ 帳號認領成功！暱稱已更新。")
                    else:
                         try:
                             supabase.table("Members").insert({"pf_id": p_id_input, "name": rn, "role": "玩家", "xp": 0, "password": rpw, "join_date": datetime.now().strftime("%Y-%m-%d")}).execute()
                             st.success("✅ 註冊成功！")
                         except:
                             st.error("❌ 該 ID 已被註冊。")
                else: st.error(f"❌ {v_msg}")

    if st.session_state.player_id:
        if st.button("🚪 退出王國"): st.session_state.player_id = None; st.query_params.clear(); st.rerun()

if not st.session_state.player_id:
    st.markdown(f"""<div class="welcome-wall"><div class="welcome-title">{m_title}</div><div class="welcome-subtitle">{m_subtitle}</div><div class="feature-box">{m_desc1}</div><div class="feature-box">{m_desc2}</div><div class="feature-box">{m_desc3}</div></div>""", unsafe_allow_html=True); st.stop()

# --- 4. 玩家主介面 ---
curr_m = datetime.now().strftime("%m")
t_p = st.tabs(["🪪 排位/VIP", "🎯 任務", "🎮 遊戲大廳", "🛒 商城", "🎒 背包", "🏆 榜單"])

nick_cost = int(get_config('nickname_cost', "500"))

with t_p[0]: # 排位卡
    u_res = supabase.table("Members").select("*").eq("pf_id", st.session_state.player_id).execute()
    u_row = u_res.data[0]
    
    h_res = supabase.table("Leaderboard").select("hero_points").eq("player_id", st.session_state.player_id).execute()
    h_pts = h_res.data[0]['hero_points'] if h_res.data else 0
    
    m_res = supabase.table("Monthly_God").select("monthly_points").eq("player_id", st.session_state.player_id).execute()
    m_pts = m_res.data[0]['monthly_points'] if m_res.data else 0
    
    player_rank_title = get_rank_v2500(h_pts)
    
    vip_lvl = int(u_row.get('vip_level', 0) or 0)
    vip_exp = u_row.get('vip_expiry')
    vip_pts = u_row.get('vip_points', 0)
    
    vip_badge_html = ""
    if vip_lvl > 0 and vip_exp:
        try:
            exp_str = str(vip_exp).split('.')[0]
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < exp_dt:
                v_name = get_config(f'vip_name_{vip_lvl}', f"LV.{vip_lvl}")
                remain = exp_dt - datetime.now()
                hours = remain.days * 24 + remain.seconds // 3600
                vip_badge_html = f'<div class="vip-badge">👑 {v_name} | 剩餘 {hours} 小時</div>'
            else:
                supabase.table("Members").update({"vip_level": 0}).eq("pf_id", st.session_state.player_id).execute()
                vip_lvl = 0
        except: pass
    
    col_vip, col_rank = st.columns(2)
    with col_vip:
        if 'vip_card_flipped' not in st.session_state: st.session_state.vip_card_flipped = False
        if st.button("💳 翻轉 VIP 卡"): st.session_state.vip_card_flipped = not st.session_state.vip_card_flipped
        
        v_name_display = "普通會員"
        if vip_lvl > 0: v_name_display = get_config(f'vip_name_{vip_lvl}', f"VIP {vip_lvl}")
            
        if not st.session_state.vip_card_flipped:
            st.markdown(f'''
            <div class="vip-card">
                <div class="vip-card-title">{v_name_display}</div>
                <div class="vip-card-info">姓名: {u_row['name']}</div>
                <div class="vip-card-info">ID: {u_row['pf_id']}</div>
                <div style="margin-top:15px; color:#FFD700; font-weight:bold;">當前 VP 點數: {vip_pts:,.0f}</div>
                <div style="font-size:0.8em; color:#AAA;">請維持活躍以保留尊榮身份</div>
                <div style="margin-top:10px;">{vip_badge_html}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
             vip_desc = get_config('vip_card_desc', 'VIP 點數可用於兌換專屬商品與特權。')
             st.markdown(f'''<div class="vip-card" style="background:#222; color:#FFD700; border-color:#FFD700;"><h3 style="border-bottom:2px solid #666; padding-bottom:10px;">VIP 權益說明</h3><p>{vip_desc}</p></div>''', unsafe_allow_html=True)

    with col_rank:
        if 'rank_card_flipped' not in st.session_state: st.session_state.rank_card_flipped = False
        if st.button("🔄 翻轉排位卡"): st.session_state.rank_card_flipped = not st.session_state.rank_card_flipped
        if not st.session_state.rank_card_flipped:
            er_res = supabase.table("Leaderboard").select("player_id", count="exact").gt("hero_points", h_pts).neq("player_id", "330999").execute()
            e_rk_val = er_res.count + 1
            
            mr_res = supabase.table("Monthly_God").select("player_id", count="exact").gt("monthly_points", m_pts).neq("player_id", "330999").execute()
            m_rk_val = mr_res.count + 1
            
            m_display_rk = f"第 {m_rk_val:,} 名"
            last_act = u_row['last_checkin']
            expire_str = "無紅利紀錄"
            if last_act and len(str(last_act)) > 10:
                try:
                    last_dt = datetime.strptime(str(last_act).split('.')[0], "%Y-%m-%d %H:%M:%S")
                    expire_dt = last_dt + timedelta(hours=72)
                    expire_str = expire_dt.strftime("%Y-%m-%d %H:%M")
                except: expire_str = "近期無變動"

            st.markdown(f'''
            <div class="rank-card">
                <h3 style="color:#FFF; margin:0;">{u_row['name']}</h3>
                <p style="color:#AAA; font-size:0.9em; margin-bottom:10px;">ID: {u_row['pf_id']}</p>
                <div style="font-size:2em; font-weight:900; color:#00FF00; margin:10px 0;">💎 {u_row['xp']:,.0f}</div>
                <div style="font-size:1.2em; color:#FF4646; margin-bottom:5px;">紅利: {u_row['xp_temp']:,.0f}</div>
                <div style="color:#AAA; font-size:0.8em; margin-bottom:15px;">⚠️ 效期: {expire_str}</div>
                <div class="stats-container">
                    <div class="stats-item">🏆 積分: {h_pts:,.1f}</div>
                    <div class="stats-item">🎖️ 排名: {e_rk_val}</div>
                    <div class="stats-item">🔥 月戰力: {m_pts:,.1f}</div>
                    <div class="stats-item">🏅 月榜: {m_display_rk}</div>
                </div>
                <div style="margin-top:20px; border-top:1px solid #444; padding-top:10px; color:gold; font-size:1.5em; font-weight:900;">{player_rank_title}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            rank_card_desc = get_config('rank_card_desc', "排位與積分規則請見遊戲大廳說明。")
            st.markdown(f"""<div class="rank-card"><h3 style="color:#FFD700;">📖 系統說明</h3><p style="color:#EEE; margin-top:20px;">{rank_card_desc}</p></div>""", unsafe_allow_html=True)

    if st.button("🎰 幸運簽到"):
        today = datetime.now().strftime("%Y-%m-%d")
        if str(u_row['last_checkin']).startswith(today): st.warning("⚠️ 已簽到")
        else:
            cons_days = u_row['consecutive_days'] or 0
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if str(u_row['last_checkin']).startswith(yesterday):
                cons_days += 1
            else:
                cons_days = 1
                
            rand_factor = random.random() ** 3 
            base_reward = int(ci_min + (ci_max - ci_min) * rand_factor)
            
            vip_bonus_pct = get_vip_bonus(vip_lvl)
            final_reward = int(base_reward * (1 + vip_bonus_pct / 100.0))
            
            bonus_msg = f" (含 VIP {vip_bonus_pct}% 加成)" if vip_bonus_pct > 0 else ""
            
            new_xp = u_row['xp'] + final_reward
            new_xp_temp = u_row['xp_temp'] + 10
            supabase.table("Members").update({
                "xp": new_xp, 
                "xp_temp": new_xp_temp, 
                "last_checkin": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "consecutive_days": cons_days
            }).eq("pf_id", st.session_state.player_id).execute()
            
            supabase.table("Prizes").insert({
                "player_id": st.session_state.player_id,
                "prize_name": f"{final_reward} XP",
                "status": "自動入帳",
                "time": datetime.now().isoformat(),
                "expire_at": "無期限",
                "source": "DailyCheckIn"
            }).execute()
            
            st.success(f"✅ 簽到成功！連續第 {cons_days} 天。獲得 {final_reward} XP{bonus_msg} + 10 紅利"); time.sleep(1); st.rerun()

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
                supabase.table("Members").update({"name": new_nick, "xp": u_row['xp'] - nick_cost}).eq("pf_id", st.session_state.player_id).execute()
                st.success("成功"); st.rerun()
            else: st.error(v_msg if not v_res else "XP 不足")

with t_p[1]: # 🎯 任務
    st.subheader("🎯 玩家任務中心")
    mis_res = supabase.table("Missions").select("*").eq("status", "Active").execute()
    missions = pd.DataFrame(mis_res.data)
    
    for m_type in ["Daily", "Weekly", "Monthly", "Season"]:
        st.markdown(f"### 📅 {m_type}")
        if not missions.empty:
            type_missions = missions[missions['type'] == m_type]
            if type_missions.empty: continue
            for _, m in type_missions.iterrows():
                is_met, is_claimed, cur_val = check_mission_status(st.session_state.player_id, m_type, m['target_criteria'], m['target_value'], m['id'])
                
                base_xp = m['reward_xp']
                vip_bonus_pct = get_vip_bonus(vip_lvl)
                final_xp = int(base_xp * (1 + vip_bonus_pct / 100.0))
                
                reward_txt = f"+{final_xp} XP"
                if vip_bonus_pct > 0: reward_txt += f" (VIP +{vip_bonus_pct}%)"
                
                if m['reward_item']: reward_txt = f"🎁 {m['reward_item']}"
                recur_txt = ""
                if m.get('recurring_months', 0) > 0 and is_claimed: recur_txt = f"(冷卻中: {m['recurring_months']} 個月後可再次領取)"
                
                col_m1, col_m2 = st.columns([8, 2])
                with col_m1:
                    st.markdown(f"""<div class="mission-card"><div><div class="mission-title">{m['title']} {recur_txt}</div><div class="mission-desc">{m['description']} (進度: {cur_val}/{m['target_value']})</div></div><div class="mission-reward">{reward_txt}</div></div>""", unsafe_allow_html=True)
                with col_m2:
                    if is_claimed: st.button("✅ 已完成", key=f"btn_claimed_{m['id']}", disabled=True)
                    elif is_met:
                        if st.button("🎁 領取獎勵", key=f"btn_claim_{m['id']}"):
                            if base_xp > 0: 
                                cur_xp = supabase.table("Members").select("xp").eq("pf_id", st.session_state.player_id).execute().data[0]['xp']
                                supabase.table("Members").update({"xp": cur_xp + final_xp}).eq("pf_id", st.session_state.player_id).execute()
                            
                            if m['reward_item']:
                                 chk_stock = supabase.table("Inventory").select("stock").eq("item_name", m['reward_item']).execute()
                                 if chk_stock.data and chk_stock.data[0]['stock'] > 0:
                                     supabase.table("Inventory").update({"stock": chk_stock.data[0]['stock'] - 1}).eq("item_name", m['reward_item']).execute()
                                     supabase.table("Prizes").insert({
                                         "player_id": st.session_state.player_id, 
                                         "prize_name": m['reward_item'], 
                                         "status": '待兌換', 
                                         "time": datetime.now().isoformat(), 
                                         "expire_at": "無期限", 
                                         "source": '任務獎勵'
                                     }).execute()
                                 else: st.error("獎品庫存不足，請聯繫管理員"); st.stop()
                            
                            supabase.table("Mission_Logs").insert({"player_id": st.session_state.player_id, "mission_id": int(m['id']), "claim_time": datetime.now().isoformat()}).execute()
                            st.balloons(); st.rerun()
                    else: st.button("🔒 未達成", key=f"btn_locked_{m['id']}", disabled=True)

with t_p[2]: # 🎮 遊戲大廳
    st.markdown(f'<div class="xp-bar">💰 當前餘額: {u_row["xp"]:,} XP</div>', unsafe_allow_html=True)
    if 'current_game' not in st.session_state: st.session_state.current_game = 'lobby'
    
    if st.session_state.current_game == 'lobby':
        st.subheader("🎮 撲洛遊戲大廳")
        s_mines = get_config('status_mines', 'ON')
        s_wheel = get_config('status_wheel', 'ON')
        s_bj = get_config('status_blackjack', 'ON')
        s_bacc = get_config('status_baccarat', 'ON')
        s_roulette = get_config('status_roulette', 'ON')

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">💣</div><div class="lobby-title">撲洛掃雷</div></div>', unsafe_allow_html=True)
            if s_mines == 'ON':
                if st.button("進入 掃雷", key="btn_mines", use_container_width=True): st.session_state.current_game = 'mines'; st.rerun()
            else: st.button("🔧 維護中", key="btn_mines_d", disabled=True, use_container_width=True)
        with c2:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🎡</div><div class="lobby-title">撲洛幸運大轉盤</div></div>', unsafe_allow_html=True)
            if s_wheel == 'ON':
                if st.button("進入 幸運大轉盤", key="btn_wheel", use_container_width=True): st.session_state.current_game = 'wheel'; st.rerun()
            else: st.button("🔧 維護中", key="btn_wheel_d", disabled=True, use_container_width=True)
        with c3:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">♠️</div><div class="lobby-title">21點 Blackjack</div></div>', unsafe_allow_html=True)
            if s_bj == 'ON':
                if st.button("進入 21點", key="btn_bj", use_container_width=True): st.session_state.current_game = 'blackjack'; st.rerun()
            else: st.button("🔧 維護中", key="btn_bj_d", disabled=True, use_container_width=True)
        
        st.write("")
        c4, c5 = st.columns(2)
        with c4:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🏛️</div><div class="lobby-title">皇家百家樂</div></div>', unsafe_allow_html=True)
            if s_bacc == 'ON':
                if st.button("進入 百家樂", key="btn_bacc", use_container_width=True): st.session_state.current_game = 'baccarat'; st.rerun()
            else: st.button("🔧 維護中", key="btn_bacc_d", disabled=True, use_container_width=True)
        with c5:
            st.markdown('<div class="lobby-card"><div class="lobby-icon">🔴</div><div class="lobby-title">俄羅斯輪盤</div></div>', unsafe_allow_html=True)
            if s_roulette == 'ON':
                 if st.button("進入 輪盤", key="btn_roulette", use_container_width=True): st.session_state.current_game = 'roulette'; st.rerun()
            else: st.button("🔧 維護中", key="btn_roulette_d", disabled=True, use_container_width=True)

    else:
        if st.button("⬅️ 返回大廳", key="back_to_lobby"): st.session_state.current_game = 'lobby'; st.rerun()

        # [CLOUD] Mines Logic
        if st.session_state.current_game == 'mines':
            st.subheader("💣 撲洛掃雷")
            if 'mines_active' not in st.session_state: st.session_state.mines_active = False
            if 'mines_revealed' not in st.session_state or len(st.session_state.mines_revealed) != 25:
                st.session_state.mines_revealed = [False] * 25
                st.session_state.mines_grid = [0] * 25
                st.session_state.mines_active = False
            if 'mines_game_over' not in st.session_state: st.session_state.mines_game_over = False
            if 'mines_multiplier' not in st.session_state: st.session_state.mines_multiplier = 1.0
            if 'mines_bet_amt' not in st.session_state: st.session_state.mines_bet_amt = 0

            with st.expander("⚙️ 遊戲設定 (點擊展開)", expanded=not st.session_state.mines_active):
                c_grid, c_bet, c_mines = st.columns(3)
                grid_opt = c_grid.selectbox("選擇戰場", ["5x5 (25格)"], disabled=st.session_state.mines_active)
                mine_bet = c_bet.number_input("投入 XP", 100, 10000, 100, disabled=st.session_state.mines_active)
                mine_count = c_mines.slider("地雷數量", 1, 24, 3, disabled=st.session_state.mines_active)

            if not st.session_state.mines_active and not st.session_state.mines_game_over:
                if st.button("🚀 開始遊戲", type="primary", use_container_width=True):
                     if u_row['xp']>=mine_bet:
                         supabase.table("Members").update({"xp": u_row['xp'] - mine_bet}).eq("pf_id", st.session_state.player_id).execute()
                         st.session_state.mines_active=True; st.session_state.mines_game_over=False
                         st.session_state.mines_grid=[0]*(25-mine_count)+[1]*mine_count; random.shuffle(st.session_state.mines_grid)
                         st.session_state.mines_revealed=[False]*25; st.session_state.mines_multiplier=1.0; st.session_state.mines_bet_amt=mine_bet; st.rerun()
                     else: st.error("XP 不足")
            elif st.session_state.mines_active:
                cur_win = int(st.session_state.mines_bet_amt * st.session_state.mines_multiplier)
                c_info, c_cash = st.columns([2, 1])
                c_info.info(f"🔥 倍率: {st.session_state.mines_multiplier:.2f}x | 💰 預期: {cur_win}")
                if c_cash.button("💰 結算", type="primary", use_container_width=True):
                    new_xp = supabase.table("Members").select("xp").eq("pf_id", st.session_state.player_id).execute().data[0]['xp']
                    supabase.table("Members").update({"xp": new_xp + cur_win}).eq("pf_id", st.session_state.player_id).execute()
                    st.session_state.mines_active=False; st.balloons(); st.success(f"贏得 {cur_win} XP"); st.rerun()
            elif st.session_state.mines_game_over:
                 st.error("💥 任務失敗！")
                 if st.button("🔄 再來一局", use_container_width=True): 
                     st.session_state.mines_game_over=False; st.session_state.mines_active=False; st.rerun()

            st.write("---")
            cols = st.columns(5)
            if len(st.session_state.mines_revealed) == 25:
                for i in range(25):
                    with cols[i%5]:
                        label = "❓"; disabled = False
                        if st.session_state.mines_revealed[i]:
                            disabled = True
                            if st.session_state.mines_grid[i] == 1: label = "💥"
                            else: label = "💎"
                        elif st.session_state.mines_game_over:
                             disabled = True
                             if st.session_state.mines_grid[i] == 1: label = "💣"
                        if st.button(label, key=f"m_{i}", disabled=disabled, use_container_width=True):
                            if not st.session_state.mines_game_over and st.session_state.mines_active:
                                st.session_state.mines_revealed[i]=True
                                if st.session_state.mines_grid[i]: 
                                    st.session_state.mines_active=False; st.session_state.mines_game_over=True; st.rerun()
                                else: 
                                    n_revealed = sum(1 for x in range(25) if st.session_state.mines_revealed[x] and st.session_state.mines_grid[x]==0)
                                    try:
                                        total_comb = math.comb(25, n_revealed)
                                        safe_comb = math.comb(25 - mine_count, n_revealed)
                                        if safe_comb > 0: st.session_state.mines_multiplier = 0.97 * (total_comb / safe_comb)
                                    except: pass
                                    st.rerun()
            else:
                st.warning("遊戲狀態重置中...請稍後"); st.session_state.mines_revealed = [False]*25; st.rerun()
        
        # [CLOUD] Wheel Logic
        elif st.session_state.current_game == 'wheel':
             st.subheader("🎡 撲洛幸運大轉盤 (小瑪莉)")
             wheel_cost = int(get_config('min_bet_wheel', "100"))
             st.info(f"消耗: {wheel_cost} XP / 次")
             p_lvl = rank_to_level(player_rank_title)
             
             inv_res = supabase.table("Inventory").select("*").gt("stock", 0).in_("target_market", ["Wheel", "Both"]).execute()
             all_items = pd.DataFrame(inv_res.data)
             
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
                     if not valid_items: st.error("獎池目前沒有適合您排位的獎品"); st.stop()
                     supabase.table("Members").update({"xp": u_row['xp'] - wheel_cost}).eq("pf_id", st.session_state.player_id).execute()
                     
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
        
        # [CLOUD] Blackjack Logic
        elif st.session_state.current_game == 'blackjack':
            st.subheader("♠️ 21點")
            if 'bj_active' not in st.session_state: st.session_state.bj_active = False
            if 'bj_game_over' not in st.session_state: st.session_state.bj_game_over = False

            if not st.session_state.bj_active:
                bet = st.number_input("下注 XP", 100, 10000, 100)
                if st.button("🃏 發牌"):
                    if u_row['xp'] >= bet:
                        # Deduct XP
                        supabase.table("Members").update({"xp": u_row['xp'] - bet}).eq("pf_id", st.session_state.player_id).execute()
                        
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
                             # Add Win
                             new_xp = supabase.table("Members").select("xp").eq("pf_id", st.session_state.player_id).execute().data[0]['xp']
                             supabase.table("Members").update({"xp": new_xp + win_amt}).eq("pf_id", st.session_state.player_id).execute()
                             st.session_state.bj_paid_flag = True
                         st.success(f"恭喜！您贏了 {win_amt} XP！"); st.balloons()
                    else: st.error(f"結果: {msg}")
                        
                    if st.button("🔄 再玩一局"):
                        st.session_state.bj_active = False
                        if 'bj_paid_flag' in st.session_state: del st.session_state.bj_paid_flag
                        st.rerun()

        # [CLOUD] Roulette Logic
        elif st.session_state.current_game == 'roulette':
            st.subheader("🔴 俄羅斯輪盤 (Roulette)")
            
            # Fetch State
            r_state = supabase.table("Roulette_Global").select("*").eq("id", 1).execute().data[0]
            hist_str = r_state['history_string'] if r_state['history_string'] else ""
            hist_list = hist_str.split(',') if hist_str else []
            
            # 1. History & Result
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

            # 2. Control Panel
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
                    # Deduct XP
                    supabase.table("Members").update({"xp": u_row['xp'] - total_bet}).eq("pf_id", st.session_state.player_id).execute()
                    
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
                        # Add Win
                        new_xp = supabase.table("Members").select("xp").eq("pf_id", st.session_state.player_id).execute().data[0]['xp']
                        supabase.table("Members").update({"xp": new_xp + total_win}).eq("pf_id", st.session_state.player_id).execute()
                        
                        supabase.table("Prizes").insert({
                            "player_id": st.session_state.player_id, 
                            "prize_name": f"{total_win} XP", 
                            "status": '自動入帳', 
                            "time": datetime.now().isoformat(), 
                            "expire_at": "無期限", 
                            "source": "GameWin-Roulette"
                        }).execute()
                    
                    # Update History
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
                if sb3.button("單數", key="rb_odd"): st.session_state.roulette_bets["單數"] = st.session_state.roulette_bets.get("單數", 0) + st.session_state.roulette_chips
                if sb4.button("雙數", key="rb_even"): st.session_state.roulette_bets["雙數"] = st.session_state.roulette_bets.get("雙數", 0) + st.session_state.roulette_chips

        # [CLOUD] Baccarat Logic
        elif st.session_state.current_game == 'baccarat':
            st.subheader("🏛️ 皇家百家樂 (Royal Baccarat)")
            
            if 'bacc_chips' not in st.session_state: st.session_state.bacc_chips = 100
            if 'bacc_bets' not in st.session_state: st.session_state.bacc_bets = {"P":0, "B":0, "T":0, "PP":0, "BP":0}
            
            # Fetch State
            b_state = supabase.table("Baccarat_Global").select("*").eq("id", 1).execute().data[0]
            hist_str = b_state['history_string'] if b_state['history_string'] else ""
            hist_list = hist_str.split(',') if hist_str else []
            hand_count = b_state['hand_count']

            st.markdown("#### 📜 牌路 (Bead Plate)")
            bead_html = "<div class='bead-plate'>"
            for h in hist_list:
                if h:
                    c = "bead-P" if h=='P' else ("bead-B" if h=='B' else "bead-T")
                    bead_html += f"<div class='bead {c}'>{h}</div>"
            bead_html += "</div>"
            st.markdown(bead_html, unsafe_allow_html=True)
            st.caption(f"目前第 {hand_count} 手 (60手後自動洗牌)")

            st.write("#### 🪙 選擇籌碼")
            chips = [100, 500, 1000, 5000, 10000]
            chip_cols = st.columns(len(chips))
            for i, chip in enumerate(chips):
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
                    # Deduct XP
                    supabase.table("Members").update({"xp": u_row['xp'] - total_bet}).eq("pf_id", st.session_state.player_id).execute()
                    
                    rtp = float(get_config('rtp_baccarat', "0.95"))
                    deck = [1,2,3,4,5,6,7,8,9,10,11,12,13] * 8; random.shuffle(deck)
                    
                    # Logic
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
                        new_xp = supabase.table("Members").select("xp").eq("pf_id", st.session_state.player_id).execute().data[0]['xp']
                        supabase.table("Members").update({"xp": new_xp + pot_win}).eq("pf_id", st.session_state.player_id).execute()
                        supabase.table("Prizes").insert({
                            "player_id": st.session_state.player_id, 
                            "prize_name": f"{pot_win} XP", 
                            "status": '自動入帳', 
                            "time": datetime.now().isoformat(), 
                            "expire_at": "無期限", 
                            "source": "GameWin-bacc"
                        }).execute()
                    
                    # Update History
                    new_hist = hist_str + "," + winner if hist_str else winner
                    new_count = hand_count + 1
                    if new_count >= 60: new_hist = ""; new_count = 0; st.toast("🔄 洗牌中...")
                    supabase.table("Baccarat_Global").update({"hand_count": new_count, "history_string": new_hist}).eq("id", 1).execute()
                    
                    log_game_transaction(st.session_state.player_id, 'baccarat', 'BET', total_bet)
                    if pot_win > 0: log_game_transaction(st.session_state.player_id, 'baccarat', 'WIN', pot_win)

                    # Animation
                    ph = st.empty(); bh = st.empty()
                    def render_card(val):
                         s = random.choice(['♠', '♣', '♥', '♦'])
                         c = "red" if s in ['♥', '♦'] else "black"
                         d = {1:'A',11:'J',12:'Q',13:'K'}.get(val, str(val))
                         return f"<div class='bacc-card {c}'>{d}<br>{s}</div>"

                    p_html = ""
                    for card in p_hand:
                        p_html += render_card(card)
                        ph.markdown(f"<div style='text-align:center'><h3>🔵 閒家</h3><div>{p_html}</div></div>", unsafe_allow_html=True)
                        time.sleep(0.5)
                    
                    b_html = ""
                    for card in b_hand:
                        b_html += render_card(card)
                        bh.markdown(f"<div style='text-align:center'><h3>🔴 莊家</h3><div>{b_html}</div></div>", unsafe_allow_html=True)
                        time.sleep(0.5)

                    res_msg = f"結果: {winner} ({p_val} vs {b_val})"
                    if pot_win > total_bet: st.success(f"贏得 {pot_win} XP! {res_msg}"); st.balloons()
                    elif pot_win == total_bet: st.info(f"退回本金 {res_msg}")
                    else: st.error(f"莊家通吃 {res_msg}")
                    
                    st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                    time.sleep(2); st.rerun()

                else: st.error("XP 不足或未下注")

with t_p[3]: # 商城
    st.subheader("🛒 商城")
    srt = st.radio("排序", ["市價高>低", "市價低>高"], horizontal=True, key="m_sort")
    asc = True if "低>高" in srt else False
    
    inv_res = supabase.table("Inventory").select("*").gt("stock", 0).in_("target_market", ["Mall", "Both"]).order("item_value", desc=(not asc)).execute()
    items = pd.DataFrame(inv_res.data)
    
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
                            supabase.table("Members").update({"xp": u_row['xp'] - final_xp_price}).eq("pf_id", st.session_state.player_id).execute()
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
    pz_res = supabase.table("Prizes").select("*").eq("player_id", st.session_state.player_id).not_.ilike("source", "GameWin%").order("id", desc=True).execute()
    prizes = pd.DataFrame(pz_res.data)
    
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
    ldf1, ldf2 = st.columns(2)
    with ldf1:
        st.markdown(f"<div class='glory-title'>{lb_title_1}</div>", unsafe_allow_html=True)
        # Join Leaderboard and Members
        lb_res = supabase.table("Leaderboard").select("player_id, hero_points, Members(name)").neq("player_id", "330999").order("hero_points", desc=True).limit(20).execute()
        
        if lb_res.data:
            for i, row in enumerate(lb_res.data):
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                curr_rank = get_rank_v2500(row['hero_points'])
                p_name = row['Members']['name'] if row.get('Members') else row['player_id']
                st.markdown(f"""<div class="lb-rank-card {style_class}"><div class="lb-badge">{badge}</div><div class="lb-info"><div class="lb-name">{p_name} <span style="font-size:0.8em;color:#DDD;">({curr_rank})</span></div><div class="lb-id">{row['player_id']}</div></div><div class="lb-score">{row['hero_points']}</div></div>""", unsafe_allow_html=True)
        else: st.info("暫無資料")

    with ldf2:
        st.markdown(f"<div class='glory-title'>{lb_title_2}</div>", unsafe_allow_html=True)
        mg_res = supabase.table("Monthly_God").select("player_id, monthly_points, Members(name)").neq("player_id", "330999").order("monthly_points", desc=True).limit(20).execute()
        
        if mg_res.data:
            for i, row in enumerate(mg_res.data):
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                p_name = row['Members']['name'] if row.get('Members') else row['player_id']
                st.markdown(f"""<div class="lb-rank-card {style_class}"><div class="lb-badge">{badge}</div><div class="lb-info"><div class="lb-name">{p_name}</div><div class="lb-id">{row['player_id']}</div></div><div class="lb-score">{row['monthly_points']}</div></div>""", unsafe_allow_html=True)
        else: st.info("暫無資料")

# --- 5. 指揮部 (Admin) ---
if st.session_state.access_level in ["老闆", "店長", "員工"]:
    st.write("---"); st.header("⚙️ 指揮部")
    user_role = st.session_state.access_level
    
    tabs = st.tabs(["💰 櫃台與物資", "👥 人員與空投", "📊 賽事與數據", "🛠️ 系統與維護"])
    
    with tabs[0]: 
        st.subheader("🛂 櫃台核銷")
        target = st.text_input("玩家 ID")
        if target:
            # 1. Fetch pending prizes
            pend_res = supabase.table("Prizes").select("id, prize_name").eq("player_id", target).eq("status", "待兌換").execute()
            prizes_data = pend_res.data
            
            display_data = []
            if prizes_data:
                # 2. Collect distinct item names
                p_names = list(set([p['prize_name'] for p in prizes_data]))
                
                # 3. Batch query inventory details (manual join to avoid APIError on missing relations)
                inv_map = {}
                if p_names:
                    try:
                        inv_res = supabase.table("Inventory").select("item_name, item_value, vip_card_level, vip_card_hours").in_("item_name", p_names).execute()
                        inv_map = {i['item_name']: i for i in inv_res.data}
                    except: pass
                
                # 4. Merge data
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
                        # VIP Logic
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

                        # XP Card Logic
                        xp_match = re.search(r'(\d+)\s*XP', str(selected_item['prize_name']), re.IGNORECASE)
                        if xp_match:
                            add_xp = int(xp_match.group(1))
                            cur_xp = supabase.table("Members").select("xp").eq("pf_id", target).execute().data[0]['xp']
                            supabase.table("Members").update({"xp": cur_xp + add_xp}).eq("pf_id", target).execute()
                            st.toast(f"💰 已自動儲值 {add_xp} XP")
                        
                        supabase.table("Prizes").update({"status": '已核銷'}).eq("id", redeem_id).execute()
                        supabase.table("Staff_Logs").insert({"staff_id": st.session_state.player_id, "player_id": target, "prize_name": selected_item['prize_name'], "time": datetime.now().isoformat()}).execute()
                        st.success("核銷作業完成！"); time.sleep(1); st.rerun()
            else: st.info("該玩家無待核銷物品")
            
            if user_role == "老闆":
                st.write("---"); st.subheader("💰 人工充值 (老闆限定)")
                xp_add = st.number_input("充值 XP", step=100)
                if st.button("執行充值"):
                    cur_xp = supabase.table("Members").select("xp").eq("pf_id", target).execute().data[0]['xp']
                    supabase.table("Members").update({"xp": cur_xp + xp_add}).eq("pf_id", target).execute()
                    st.success("已充值")
            
            st.write("---"); st.subheader("📜 櫃台核銷歷史查詢")
            hd1 = st.date_input("起始日期")
            hd2 = st.date_input("結束日期")
            if st.button("查詢歷史紀錄"):
                 hq_start = hd1.strftime("%Y-%m-%d 00:00:00"); hq_end = hd2.strftime("%Y-%m-%d 23:59:59")
                 logs_res = supabase.table("Staff_Logs").select("*").gte("time", hq_start).lte("time", hq_end).order("time", desc=True).execute()
                 st.dataframe(pd.DataFrame(logs_res.data))
                 
                 if user_role == "老闆" and logs_res.data:
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
            inv_res = supabase.table("Inventory").select("*").execute()
            if inv_res.data:
                for mm in inv_res.data:
                    with st.expander(f"{mm['item_name']} (庫存: {mm['stock']})"):
                        c1, c2, c3, c4 = st.columns(4)
                        new_p = c1.number_input(f"XP售價", value=int(mm['mall_price']), key=f"mm_p_{mm['item_name']}")
                        new_vp = c2.number_input(f"VP售價", value=int(mm.get('vip_price', 0)), key=f"mm_vp_{mm['item_name']}")
                        new_s = c3.number_input(f"庫存", value=mm['stock'], key=f"mm_s_{mm['item_name']}")
                        
                        r_idx = ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"].index(mm.get('mall_min_rank', '無限制'))
                        new_r = c4.selectbox(f"限制", ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"], index=r_idx, key=f"mm_r_{mm['item_name']}")
                        
                        c5, c6, c7 = st.columns([2, 1, 1])
                        new_u = c5.text_input("圖片", value=mm['img_url'], key=f"mm_u_{mm['item_name']}")
                        new_st = c6.selectbox("狀態", ["上架中", "下架中"], index=0 if mm['status']=='上架中' else 1, key=f"mm_st_{mm['item_name']}")
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
            mem_res = supabase.table("Members").select("*").eq("pf_id", q).execute()
            if mem_res.data:
                mem = mem_res.data[0]
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
                tr_res = supabase.table("Tournament_Records").select("actual_fee").eq("player_id", q).execute()
                total_contribution = sum(r['actual_fee'] for r in tr_res.data)
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
                             supabase.table("Members").update({"xp": mem['xp'] - deduct_xp}).eq("pf_id", q).execute()
                             st.success("已扣除"); st.rerun()

                with st.expander("🎰 近 20 場遊戲紀錄"):
                    gw = supabase.table("Prizes").select("source, prize_name, time").eq("player_id", q).ilike("source", "GameWin%").order("id", desc=True).limit(20).execute()
                    st.table(pd.DataFrame(gw.data))
                
                with st.expander("🎒 背包庫存"):
                    bp = supabase.table("Prizes").select("prize_name, status, expire_at").eq("player_id", q).eq("status", "待兌換").order("id", desc=True).execute()
                    st.table(pd.DataFrame(bp.data))

            else: st.error("無此人")

        st.write("---")
        st.subheader("🚀 物資空投")
        target_group = st.selectbox("發送對象", ["單一玩家 ID", "全體玩家", "🏆 菁英", "🎖️ 大師", "💎 鑽石", "⬜ 白金", "🥈 白銀", "VIP 1 (銅)", "VIP 2 (銀)", "VIP 3 (金)", "VIP 4 (鑽)"])
        
        target_ids = []
        if target_group == "單一玩家 ID":
            tid = st.text_input("輸入玩家 ID")
            if tid: target_ids = [tid]
        elif target_group == "全體玩家":
            res = supabase.table("Members").select("pf_id").execute()
            target_ids = [r['pf_id'] for r in res.data]
        else:
            if "VIP" in target_group:
                lvl = int(target_group.split(" ")[2])
                res = supabase.table("Members").select("pf_id").eq("vip_level", lvl).execute()
                target_ids = [r['pf_id'] for r in res.data]
            
        st.info(f"預計發送對象人數: {len(target_ids)} 人")
        
        c_xp, c_vp, c_it = st.columns(3)
        xp = c_xp.number_input("XP 點數", 0)
        vp = c_vp.number_input("VIP 點數", 0)
        inv_list = supabase.table("Inventory").select("item_name").execute()
        it = c_it.selectbox("禮物 (庫存)", ["無"] + [i['item_name'] for i in inv_list.data])
        
        if st.button("確認空投"):
            if not target_ids: st.error("無目標")
            else:
                for t in target_ids:
                    if xp or vp:
                        mem = supabase.table("Members").select("xp, vip_points").eq("pf_id", t).execute().data[0]
                        upd = {}
                        if xp: upd["xp"] = mem['xp'] + xp
                        if vp: upd["vip_points"] = mem['vip_points'] + vp
                        supabase.table("Members").update(upd).eq("pf_id", t).execute()
                    
                    if it != "無":
                         # Deduct stock
                         cur_s = supabase.table("Inventory").select("stock").eq("item_name", it).execute().data[0]['stock']
                         supabase.table("Inventory").update({"stock": cur_s - 1}).eq("item_name", it).execute()
                         # Add prize
                         supabase.table("Prizes").insert({
                             "player_id": t, "prize_name": it, "status": '待兌換', 
                             "time": datetime.now().isoformat(), "expire_at": "無期限", "source": '老闆空投'
                         }).execute()
                st.success("空投完成")

    with tabs[2]: # 賽事與數據
        st.subheader("📁 賽事精算導入"); up = st.file_uploader("上傳 CSV / Excel")
        if up and st.button("執行精算"):
            try:
                fn = up.name; buy = int(re.search(r'(1200|3400|6600|11000|21500)', fn).group(1))
                if fn.endswith('.csv'):
                    try: df = pd.read_csv(up, encoding='utf-8-sig')
                    except: 
                        up.seek(0)
                        df = pd.read_csv(up, encoding='big5')
                else: df = pd.read_excel(up)
                
                df.columns = df.columns.str.strip()
                
                chk = supabase.table("Import_History").select("filename").eq("filename", fn).execute()
                if chk.data:
                    st.error(f"❌ 檔案 {fn} 已被匯入過！"); st.stop()
                
                matrix = {1200: (200, 0.75, [2, 1.5, 1]), 3400: (400, 1.5, [5, 4, 3]), 6600: (600, 2.0, [10, 8, 6]), 11000: (1000, 3.0, [20, 15, 10]), 21500: (1500, 5.0, [40, 30, 20])}
                base, p_mult, bonuses = matrix.get(buy, (100, 1.0, [1, 1, 1]))
                
                for _, r in df.iterrows():
                    pid = str(r['ID']); raw_name = str(r['Nickname']); name = raw_name[:10]
                    # Ensure Member exists
                    mem = supabase.table("Members").select("pf_id").eq("pf_id", pid).execute()
                    if not mem.data:
                        supabase.table("Members").insert({"pf_id": pid, "name": name, "role": "玩家", "xp": 0}).execute()
                    
                    rank = int(r['Rank'])
                    re_e = int(r.get('Re-Entries', 0))
                    payout = int(r.get('Payout', 0))
                    
                    # Update XP (simplified: update += payout)
                    cur_xp = supabase.table("Members").select("xp").eq("pf_id", pid).execute().data[0]['xp']
                    supabase.table("Members").update({"xp": cur_xp + payout}).eq("pf_id", pid).execute()
                    
                    # Calculate Points
                    pts = 0
                    if rank == 1: pts = bonuses[0]
                    elif rank == 2: pts = bonuses[1]
                    elif rank == 3: pts = bonuses[2]
                    
                    # Update Leaderboard
                    lb_chk = supabase.table("Leaderboard").select("hero_points").eq("player_id", pid).execute()
                    if lb_chk.data:
                         supabase.table("Leaderboard").update({"hero_points": lb_chk.data[0]['hero_points'] + pts}).eq("player_id", pid).execute()
                    else:
                         supabase.table("Leaderboard").insert({"player_id": pid, "hero_points": pts}).execute()
                    
                    # Log
                    supabase.table("Tournament_Records").insert({
                        "player_id": pid, "buy_in": buy, "rank": rank, "re_entries": re_e, "payout": payout, "filename": fn,
                        "actual_fee": (1 + re_e) * int(buy * 0.2), # Approx fee
                        "time": datetime.now().isoformat()
                    }).execute()
                
                supabase.table("Import_History").insert({"filename": fn, "import_time": datetime.now().isoformat()}).execute()
                st.balloons(); st.success(f"✅ 成功匯入 {fn}")

            except Exception as e: st.error(f"匯入失敗: {e}")

    with tabs[3]: # 系統設定
        st.subheader("⚙️ 遊戲參數微調")
        
        # Simple loop to generate UI for settings
        settings_map = {
            "marquee_text": "跑馬燈文字",
            "marquee_speed": "跑馬燈速度 (秒)",
            "welcome_title": "首頁大標題",
            "rtp_blackjack": "21點 RTP (0.1~1.0)",
            "rtp_roulette": "輪盤 RTP",
            "rtp_baccarat": "百家樂 RTP"
        }
        
        for k, v in settings_map.items():
            curr = get_config(k, "")
            new_val = st.text_input(v, value=curr)
            if st.button(f"更新 {k}"):
                set_config(k, new_val)
                st.success("已更新")
        
        st.write("---")
        st.markdown("**緊急開關**")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🔥 重置所有排行榜"):
            if st.checkbox("確認重置?"):
                supabase.table("Leaderboard").delete().neq("player_id", "xxxx").execute() 
                st.warning("排行榜已重置")

        if c2.button("📅 重置月榜"):
            if st.checkbox("確認重置月榜?", key="chk_m_god"):
                supabase.table("Monthly_God").delete().neq("player_id", "xxxx").execute()
                st.warning("✅ 月度戰神榜已重置歸零")

        if c3.button("🧹 清空交易紀錄"):
            if st.checkbox("確認清空?", key="chk_logs"):
                supabase.table("Game_Transactions").delete().neq("id", 0).execute()
                st.warning("✅ 所有遊戲交易紀錄已清空")

        if c4.button("🔄 全域補貨(100)"):
            if st.checkbox("確認補貨?", key="chk_stock"):
                supabase.table("Inventory").update({"stock": 100}).gt("stock", -1).execute()
                st.warning("✅ 所有商品庫存已重置為 100")