import streamlit as st
import pandas as pd
import random
import re
import time
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

# --- 2. 核心：快取與背景執行 ---

@st.cache_data(ttl=60) # 縮短快取時間以便設定能更快生效
def get_all_settings():
    """快取系統設定"""
    try:
        response = supabase.table("System_Settings").select("*").execute()
        return {item['config_key']: item['config_value'] for item in response.data}
    except: return {}

def get_config(key, default_value):
    # 每次呼叫都重新讀取快取（如果過期會自動重抓）
    settings = get_all_settings()
    return settings.get(key, default_value)

def set_config(key, value):
    try:
        supabase.table("System_Settings").upsert({"config_key": key, "config_value": str(value)}).execute()
        get_all_settings.clear() # 清除快取
    except Exception as e: print(f"Config Error: {e}")

def get_current_user_data(player_id):
    """讀取玩家資料"""
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
        </style>
        <div class="welcome-wall" style="text-align:center; padding:60px 20px; background:linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.9)), url('{m_bg}'); background-size:cover; border-radius:20px; border:2px solid #FFD700; margin-bottom:20px;">
            <div style="font-size:3.5em; font-weight:900; color:#FFD700;">{m_title}</div>
            <div style="font-size:1.5em; color:#EEE;">{m_subtitle}</div>
        </div>
        <div class="marquee-container"><div class="marquee-text">{m_txt}</div></div>
    """, unsafe_allow_html=True)
    return lb_title_1, lb_title_2, ci_min, ci_max

def get_rank_v2500(pts):
    # [修復] 從設定讀取排位分數門檻
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
        if 'vip_card_flipped' not in st.session_state: st.session_state.vip_card_flipped = False
        if st.button("💳 翻轉 VIP 卡"): st.session_state.vip_card_flipped = not st.session_state.vip_card_flipped
        
        if not st.session_state.vip_card_flipped:
            st.markdown(f'''<div class="vip-card"><h3>{u_row['name']}</h3><p>ID: {u_row['pf_id']}</p><h2>VIP {vip_lvl}</h2><p>VP: {u_row.get('vip_points', 0):,.0f}</p></div>''', unsafe_allow_html=True)
        else:
            # [修復] 顯示自定義 VIP 說明
            v_desc = get_config('vip_card_desc', 'VIP 點數可用於兌換專屬商品與特權。')
            st.markdown(f'''<div class="vip-card"><h3>VIP 權益說明</h3><p>{v_desc}</p></div>''', unsafe_allow_html=True)

    with c2:
        if 'rank_card_flipped' not in st.session_state: st.session_state.rank_card_flipped = False
        if st.button("🔄 翻轉排位卡"): st.session_state.rank_card_flipped = not st.session_state.rank_card_flipped
        
        if not st.session_state.rank_card_flipped:
            st.markdown(f'''<div class="rank-card"><h3>{player_rank_title}</h3><h1 style="color:#00FF00;">💎 {u_row['xp']:,.0f}</h1><p>積分: {h_pts}</p><p>月積分: {m_pts}</p></div>''', unsafe_allow_html=True)
        else:
            # [修復] 顯示自定義排位說明
            r_desc = get_config('rank_card_desc', '排位與積分規則請見遊戲大廳說明。')
            st.markdown(f'''<div class="rank-card"><h3>系統說明</h3><p>{r_desc}</p></div>''', unsafe_allow_html=True)

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

        if st.session_state.current_game == 'mines':
            st.subheader("💣 撲洛掃雷")
            if 'mines_active' not in st.session_state: st.session_state.mines_active = False
            if 'mines_revealed' not in st.session_state or len(st.session_state.mines_revealed) != 25:
                st.session_state.mines_revealed = [False] * 25
                st.session_state.mines_grid = [0] * 25
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
                    st.success(f"贏得 {cur_win} XP"); st.rerun()

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
            
            if not st.session_state.bj_active:
                bet = st.number_input("下注 XP", 100, 10000, 100)
                if st.button("🃏 發牌"):
                    if u_row['xp'] >= bet:
                        update_user_xp(st.session_state.player_id, -bet)
                        st.session_state.bj_active = True
                        st.session_state.bj_bet = bet
                        st.session_state.bj_deck = [(r,s) for r in ['2','3','4','5','6','7','8','9','10','J','Q','K','A'] for s in ['♠','♥','♦','♣']]
                        random.shuffle(st.session_state.bj_deck)
                        st.session_state.bj_p = [st.session_state.bj_deck.pop(), st.session_state.bj_deck.pop()]
                        st.session_state.bj_d = [st.session_state.bj_deck.pop(), st.session_state.bj_deck.pop()]
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
                d_val = hand_val(st.session_state.bj_d) if not st.session_state.get('bj_done') else hand_val(st.session_state.bj_d)
                
                st.write(f"莊家: {d_val if st.session_state.get('bj_done') else '?'}")
                st.write(str(st.session_state.bj_d if st.session_state.get('bj_done') else [st.session_state.bj_d[0], '?']))
                st.write("---")
                st.write(f"你: {p_val}")
                st.write(str(st.session_state.bj_p))
                
                if st.session_state.get('bj_done'):
                    if st.button("再來"): 
                        st.session_state.bj_active = False
                        del st.session_state.bj_done
                        st.rerun()
                else:
                    if p_val > 21:
                        st.error("爆牌！輸了")
                        st.session_state.bj_done = True
                        st.rerun()
                    
                    c1, c2 = st.columns(2)
                    if c1.button("🔥 要牌"):
                        st.session_state.bj_p.append(st.session_state.bj_deck.pop())
                        st.rerun()
                    if c2.button("✋ 停牌"):
                        while hand_val(st.session_state.bj_d) < 17:
                             st.session_state.bj_d.append(st.session_state.bj_deck.pop())
                        d_final = hand_val(st.session_state.bj_d)
                        win = 0
                        if d_final > 21 or p_val > d_final: win = 2
                        elif p_val == d_final: win = 1
                        
                        if win > 0:
                            amt = int(st.session_state.bj_bet * win)
                            update_user_xp(st.session_state.player_id, amt)
                            st.success(f"贏了 {amt} XP!")
                        else: st.error("莊家勝")
                        st.session_state.bj_done = True
                        st.rerun()

        elif st.session_state.current_game == 'baccarat':
            st.subheader("🏛️ 皇家百家樂")
            if 'bacc_chips' not in st.session_state: st.session_state.bacc_chips = 100
            if 'bacc_bets' not in st.session_state: st.session_state.bacc_bets = {"P":0, "B":0, "T":0, "PP":0, "BP":0}
            
            st.write("#### 🪙 選擇籌碼")
            chips = [100, 500, 1000, 5000, 10000]
            c_cols = st.columns(len(chips))
            for i, c in enumerate(chips):
                if c_cols[i].button(str(c)): st.session_state.bacc_chips = c
            st.info(f"當前籌碼: {st.session_state.bacc_chips}")

            c1, c2, c3, c4, c5 = st.columns(5)
            def add_bet(target): st.session_state.bacc_bets[target] += st.session_state.bacc_chips
            
            with c1: st.button("閒 (1:1)", on_click=add_bet, args=("P",), use_container_width=True)
            with c2: st.button("莊 (1:0.95)", on_click=add_bet, args=("B",), use_container_width=True)
            with c3: st.button("和 (1:8)", on_click=add_bet, args=("T",), use_container_width=True)
            with c4: st.button("閒對 (1:11)", on_click=add_bet, args=("PP",), use_container_width=True)
            with c5: st.button("莊對 (1:11)", on_click=add_bet, args=("BP",), use_container_width=True)
            
            st.write(f"下注狀況: {st.session_state.bacc_bets}")

            if st.button("💰 發牌"):
                total = sum(st.session_state.bacc_bets.values())
                if total > 0 and u_row['xp'] >= total:
                    update_user_xp(st.session_state.player_id, -total)
                    
                    # 簡易百家樂邏輯
                    p_val = random.randint(0, 9)
                    b_val = random.randint(0, 9)
                    winner = "T"
                    if p_val > b_val: winner = "P"
                    elif b_val > p_val: winner = "B"
                    
                    payout = 0
                    if winner == "P": payout += st.session_state.bacc_bets['P'] * 2
                    if winner == "B": payout += int(st.session_state.bacc_bets['B'] * 1.95)
                    if winner == "T": payout += st.session_state.bacc_bets['T'] * 9
                    if winner == "T": payout += st.session_state.bacc_bets['P'] + st.session_state.bacc_bets['B']
                    
                    if payout > 0:
                        update_user_xp(st.session_state.player_id, payout)
                        st.success(f"贏得 {payout} XP！結果: {winner} (閒{p_val} vs 莊{b_val})")
                    else: st.error(f"莊家吃！結果: {winner} (閒{p_val} vs 莊{b_val})")
                    st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                else: st.error("餘額不足或未下注")

        elif st.session_state.current_game == 'roulette':
            st.subheader("🔴 俄羅斯輪盤")
            if 'roulette_bets' not in st.session_state: st.session_state.roulette_bets = {} 
            if 'roulette_chips' not in st.session_state: st.session_state.roulette_chips = 100
            
            chips = [100, 500, 1000, 5000, 10000]
            c_cols = st.columns(len(chips))
            for i, c in enumerate(chips):
                if c_cols[i].button(str(c), key=f"r_c_{c}"): st.session_state.roulette_chips = c
            
            st.info(f"當前籌碼: {st.session_state.roulette_chips} | 總下注: {sum(st.session_state.roulette_bets.values())}")
            
            c1, c2, c3 = st.columns(3)
            if c1.button("🔴 紅 (Red)"): st.session_state.roulette_bets["Red"] = st.session_state.roulette_bets.get("Red", 0) + st.session_state.roulette_chips
            if c2.button("⚫ 黑 (Black)"): st.session_state.roulette_bets["Black"] = st.session_state.roulette_bets.get("Black", 0) + st.session_state.roulette_chips
            if c3.button("清除"): st.session_state.roulette_bets = {}
            
            if st.button("🚀 旋轉"):
                total = sum(st.session_state.roulette_bets.values())
                if total > 0 and u_row['xp'] >= total:
                    update_user_xp(st.session_state.player_id, -total)
                    
                    res = random.randint(0, 36)
                    red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                    total_win = 0
                    
                    for t, amt in st.session_state.roulette_bets.items():
                        win = False
                        if t == "Red" and res in red_nums: win = True
                        elif t == "Black" and res not in red_nums and res != 0: win = True
                        if win: total_win += amt * 2
                        
                    if total_win > 0:
                        update_user_xp(st.session_state.player_id, total_win)
                        st.success(f"開出 {res}！贏得 {total_win} XP")
                    else: st.error(f"開出 {res}，未中獎")
                    st.session_state.roulette_bets = {}
                else: st.error("餘額不足")

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
        st.markdown(f"### {lb_title_1}")
        lb = supabase.table("Leaderboard").select("player_id, hero_points").neq("player_id", "330999").order("hero_points", desc=True).limit(20).execute()
        st.dataframe(pd.DataFrame(lb.data))
    with c2:
        st.markdown(f"### {lb_title_2}")
        mg = supabase.table("Monthly_God").select("player_id, monthly_points").neq("player_id", "330999").order("monthly_points", desc=True).limit(20).execute()
        st.dataframe(pd.DataFrame(mg.data))

# --- 5. 指揮部 (Admin) ---
if st.session_state.access_level in ["老闆", "店長", "員工"]:
    st.write("---"); st.header("⚙️ 指揮部")
    
    with st.expander("🛂 櫃台核銷"):
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
            
            if user_role == "老闆" and st.button("充值 1000 XP"):
                update_user_xp(tid, 1000)
                st.success("已充值")

    # [修復] 遊戲大廳後台設定
    if user_role == "老闆":
        with st.expander("🎮 遊戲大廳參數設定"):
            c1, c2 = st.columns(2)
            c1.number_input("輪盤 RTP", value=float(get_config('rtp_roulette', 0.95)), key='rtp_r_in')
            c2.number_input("百家樂 RTP", value=float(get_config('rtp_baccarat', 0.95)), key='rtp_b_in')
            
            if st.button("保存遊戲參數"):
                set_config('rtp_roulette', st.session_state.rtp_r_in)
                set_config('rtp_baccarat', st.session_state.rtp_b_in)
                st.success("參數已更新")

    # [修復] 卡片說明與排位分數設定
    if user_role == "老闆":
        with st.expander("🎨 卡片與排位設定"):
            st.subheader("📝 卡片背面說明")
            rank_desc = st.text_area("排位卡說明", value=get_config('rank_card_desc', '排位與積分規則說明...'))
            vip_desc = st.text_area("VIP卡說明", value=get_config('vip_card_desc', 'VIP權益說明...'))
            
            st.subheader("🏆 排位分數門檻")
            c1, c2, c3, c4 = st.columns(4)
            r_chal = c1.number_input("菁英分數", value=int(get_config('rank_limit_challenger', 1000)))
            r_mast = c2.number_input("大師分數", value=int(get_config('rank_limit_master', 500)))
            r_diam = c3.number_input("鑽石分數", value=int(get_config('rank_limit_diamond', 200)))
            r_plat = c4.number_input("白金分數", value=int(get_config('rank_limit_platinum', 80)))
            
            if st.button("保存卡片與排位設定"):
                set_config('rank_card_desc', rank_desc)
                set_config('vip_card_desc', vip_desc)
                set_config('rank_limit_challenger', r_chal)
                set_config('rank_limit_master', r_mast)
                set_config('rank_limit_diamond', r_diam)
                set_config('rank_limit_platinum', r_plat)
                st.success("設定已更新")

    # [修復] 任務新增功能
    with st.expander("📜 任務管理"):
        st.write("➕ 新增任務")
        with st.form("add_mission"):
            t = st.text_input("標題")
            d = st.text_input("描述")
            xp = st.number_input("獎勵 XP", value=100)
            tp = st.selectbox("類型", ["Daily", "Weekly", "Monthly"])
            crit = st.selectbox("條件", ["daily_checkin", "consecutive_checkin", "daily_win"])
            val = st.number_input("目標值", value=1)
            if st.form_submit_button("新增"):
                supabase.table("Missions").insert({
                    "title": t, "description": d, "reward_xp": xp, "type": tp, 
                    "target_criteria": crit, "target_value": val, "status": "Active"
                }).execute()
                st.success("任務已新增")

    # [修復] 賽事精算導入 (含公式顯示與雙榜更新)
    with st.expander("📁 賽事精算導入"):
        st.info("""
        **🧮 積分計算公式 (雙榜同步)：**
        `積分 = 底分 + (底分 * (1/名次) * 權重) + (底分 * 重購次數)`
        
        **💰 XP 獎勵公式：**
        `XP = 獎金(Payout) + (實際費用 * 10% 回饋)`
        """)
        
        up = st.file_uploader("上傳 CSV/Excel")
        if up and st.button("執行精算"):
            try:
                if up.name.endswith('.csv'): df = pd.read_csv(up)
                else: df = pd.read_excel(up)
                
                # 這裡模擬讀取檔名中的 BuyIn，若無則預設
                buyin = 1000
                match = re.search(r'(\d+)', up.name)
                if match: buyin = int(match.group(1))
                
                # 積分矩陣 (模擬 SQLite 版邏輯)
                base = 100 if buyin < 3000 else 200
                mult = 1.5
                
                for _, r in df.iterrows():
                    pid = str(r['ID'])
                    rank = int(r['Rank'])
                    re_entry = int(r.get('Re-Entries', 0))
                    payout = int(r.get('Payout', 0))
                    actual_fee = int(buyin * 0.2 * (1 + re_entry)) # 假設服務費邏輯
                    
                    # 1. 計算積分
                    points = int(base + (base * (1/rank) * mult) + (base * re_entry))
                    
                    # 2. 計算 XP
                    xp_reward = int(payout + (actual_fee * 0.1))
                    
                    # 3. 更新 DB (雙榜 + XP)
                    # 更新 XP
                    update_user_xp(pid, xp_reward)
                    
                    # 更新總榜
                    try:
                        cur_h = supabase.table("Leaderboard").select("hero_points").eq("player_id", pid).execute().data[0]['hero_points']
                        supabase.table("Leaderboard").update({"hero_points": cur_h + points}).eq("player_id", pid).execute()
                    except:
                        supabase.table("Leaderboard").insert({"player_id": pid, "hero_points": points}).execute()
                        
                    # [修復] 更新月榜
                    try:
                        cur_m = supabase.table("Monthly_God").select("monthly_points").eq("player_id", pid).execute().data[0]['monthly_points']
                        supabase.table("Monthly_God").update({"monthly_points": cur_m + points}).eq("player_id", pid).execute()
                    except:
                        supabase.table("Monthly_God").insert({"player_id": pid, "monthly_points": points}).execute()
                        
                st.success("✅ 賽事結算完成！雙榜與 XP 皆已更新。")
            except Exception as e: st.error(f"匯入錯誤: {e}")

    # [新增] 老闆一鍵重置
    if user_role == "老闆":
        st.write("---")
        st.markdown("### 🧨 危險操作區")
        if st.button("🔥 刪除所有玩家數據 (保留老闆)", type="primary"):
            # 依序刪除關聯資料，最後刪除 Members
            supabase.table("Prizes").delete().neq("player_id", "330999").execute()
            supabase.table("Game_Transactions").delete().neq("player_id", "330999").execute()
            supabase.table("Leaderboard").delete().neq("player_id", "330999").execute()
            supabase.table("Monthly_God").delete().neq("player_id", "330999").execute()
            supabase.table("Mission_Logs").delete().neq("player_id", "330999").execute()
            # 最後刪除玩家
            supabase.table("Members").delete().neq("pf_id", "330999").execute()
            st.toast("💥 所有測試數據已清除！")