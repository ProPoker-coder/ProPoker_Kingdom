import streamlit as st
import pandas as pd
import sqlite3
import random
import re
import time
import io
import os
import base64
import json
import math
from datetime import datetime, timedelta

# --- 0. 系統核心配置 ---
st.set_page_config(
    page_title="PRO POKER 撲洛王國", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. 旗艦視覺系統 ---
def init_flagship_ui():
    with sqlite3.connect('poker_data.db') as conn:
        c = conn.cursor()
        
        m_spd = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_speed'").fetchone() or ("35",))[0]
        m_bg = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'welcome_bg_url'").fetchone() or ("https://img.freepik.com/free-photo/poker-table-dark-atmosphere_23-2151003784.jpg",))[0]
        m_title = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'welcome_title'").fetchone() or ("PRO POKER",))[0]
        m_subtitle = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'welcome_subtitle'").fetchone() or ("撲 洛 傳 奇 殿 堂",))[0]
        
        lb_title_1 = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'leaderboard_title_1'").fetchone() or ("🎖️ 菁英總榜",))[0]
        lb_title_2 = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'leaderboard_title_2'").fetchone() or ("🔥 月度戰神",))[0]

        m_desc1 = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'lobby_desc_1'").fetchone() or ("♠️ 頂級賽事體驗",))[0]
        m_desc2 = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'lobby_desc_2'").fetchone() or ("♥ 公平公正競技",))[0]
        m_desc3 = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'lobby_desc_3'").fetchone() or ("♦ 專屬尊榮服務",))[0]

        m_mode = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_mode'").fetchone() or ("custom",))[0]
        m_txt = (c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_text'").fetchone() or ("撲洛王國營運中，歡迎回歸領地！",))[0]
        
        if m_mode == 'auto':
            try:
                th_xp = int((c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_th_xp'").fetchone() or ("5000",))[0])
                th_val = int((c.execute("SELECT config_value FROM System_Settings WHERE config_key = 'marquee_th_val'").fetchone() or ("10000",))[0])
                recent_wins = pd.read_sql_query("SELECT P.player_id, M.name, P.prize_name, P.source, I.item_value FROM Prizes P LEFT JOIN Members M ON P.player_id = M.pf_id LEFT JOIN Inventory I ON P.prize_name = I.item_name ORDER BY P.id DESC LIMIT 50", conn)
                found_news = False
                for _, row in recent_wins.iterrows():
                    is_big_win = False
                    xp_match = re.search(r'(\d+)\s*XP', str(row['prize_name']), re.IGNORECASE)
                    if xp_match and int(xp_match.group(1)) >= th_xp: is_big_win = True
                    if row['item_value'] and row['item_value'] >= th_val: is_big_win = True
                    if is_big_win:
                        m_txt = f"🎉 恭喜玩家 【{row['name']}】 在 {row['source']} 中獲得大獎：{row['prize_name']}！ 🔥"
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
            .feature-box {{ display: inline-block; margin: 10px; padding: 10px 20px; background: rgba(0,0,0,0.7); border: 1px solid #555; border-radius: 50px; color: #FFF; }}

            .rank-card {{ background: linear-gradient(135deg, #1a1a1a 0%, #000 100%); border: 2px solid #FFD700; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 0 20px rgba(255, 215, 0, 0.15); height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-card {{ background: linear-gradient(135deg, #000 0%, #222 100%); border: 2px solid #9B30FF; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 0 20px rgba(155, 48, 255, 0.2); height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .vip-badge {{ background: linear-gradient(45deg, #FFD700, #FDB931); color: #000; padding: 5px 15px; border-radius: 15px; font-weight: 900; display: inline-block; margin-bottom: 15px; box-shadow: 0 0 10px gold; }}
            .xp-sub {{ font-size: 1.2em; color: #FF4646; font-weight: bold; margin-top: 5px; }}
            .stats-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
            .stats-item {{ background: rgba(255,255,255,0.05); border: 1px solid #444; padding: 8px; border-radius: 8px; font-size: 0.9em; }}

            .mall-card {{ background: #151515; border: 1px solid #333; border-radius: 12px; padding: 15px; text-align: center; height: 100%; display:flex; flex-direction:column; justify-content:space-between; }}
            .mall-card:hover {{ border-color: #FFD700; transform: translateY(-5px); }}
            .mall-price {{ color: #00FF00; font-weight: bold; font-size: 1.2em; }}
            .vip-price {{ color: #9B30FF; font-weight: bold; font-size: 1.1em; }}
            .mall-img {{ width: 100%; height: 120px; object-fit: contain; margin-bottom: 10px; border-radius: 8px; }}
            .redemption-ticket {{ background-color: #1a1a1a; border: 1px solid #444; border-left: 6px solid #00FF00; padding: 15px; border-radius: 10px; margin-bottom: 12px; }}
            
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

            .roulette-bet-table {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; max-width: 600px; margin: auto; padding: 20px; background: #0a3311; border: 5px solid #d4af37; border-radius: 15px; }}
            .r-btn {{ padding: 15px; border-radius: 5px; text-align: center; font-weight: bold; cursor: pointer; border: 1px solid #fff; color: white; transition: 0.2s; user-select: none; }}
            .r-btn:hover {{ filter: brightness(1.2); transform: scale(1.05); }}
            .r-red {{ background-color: #D40000; }}
            .r-black {{ background-color: #111; }}
            .r-green {{ background-color: #008000; grid-column: span 3; }}
            .r-active-chip {{ transform: scale(1.2); box-shadow: 0 0 15px #FFD700; border-style: solid; }}
            .roulette-history-bar {{ display: flex; gap: 5px; overflow-x: auto; padding: 10px; background: #000; border-radius: 8px; margin-bottom: 10px; border: 1px solid #333; }}
            .hist-ball {{ min-width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #fff; margin-right: 5px; }}
            .roulette-wheel-anim {{ width: 200px; height: 200px; border-radius: 50%; border: 10px dashed #FFD700; margin: 20px auto; animation: spin-ball 2s cubic-bezier(0.25, 0.1, 0.25, 1); background: radial-gradient(circle, #000 40%, #0d2b12 100%); display: flex; align-items: center; justify-content: center; font-size: 3em; color: #FFF; font-weight: bold; }}
            @keyframes spin-ball {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(3600deg); }} }}
            
            .lm-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; padding: 20px; background: #000; border: 4px solid #FFD700; border-radius: 20px; }}
            .lm-cell {{ background: #222; border: 2px solid #444; border-radius: 10px; padding: 10px; text-align: center; color: #FFF; transition: 0.1s; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
            .lm-active {{ background: #FFF; border-color: #FFD700; color: #000; box-shadow: 0 0 20px #FFD700; transform: scale(1.1); font-weight: bold; }}
            .lm-img {{ width: 50px; height: 50px; object-fit: contain; margin-bottom: 5px; }}
            
            .mine-btn {{ width: 100%; aspect-ratio: 1; border-radius: 8px; border: 2px solid #444; background: #222; font-size: 1.5em; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; }}
            .mine-btn:hover {{ border-color: #FFD700; background: #333; }}
            .mine-revealed {{ background: #111; border-color: #666; cursor: default; }}
            .mine-boom {{ background: #500; border-color: #F00; animation: shake 0.5s; }}
            .mine-safe {{ background: #050; border-color: #0F0; }}
            @keyframes shake {{ 0% {{ transform: translate(1px, 1px) rotate(0deg); }} 10% {{ transform: translate(-1px, -2px) rotate(-1deg); }} 20% {{ transform: translate(-3px, 0px) rotate(1deg); }} 30% {{ transform: translate(3px, 2px) rotate(0deg); }} 40% {{ transform: translate(1px, -1px) rotate(1deg); }} 50% {{ transform: translate(-1px, 2px) rotate(-1deg); }} 60% {{ transform: translate(-3px, 1px) rotate(0deg); }} 70% {{ transform: translate(3px, 1px) rotate(-1deg); }} 80% {{ transform: translate(-1px, -1px) rotate(1deg); }} 90% {{ transform: translate(1px, 2px) rotate(0deg); }} 100% {{ transform: translate(1px, -2px) rotate(-1deg); }} }}

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
            
            .wheel-item-card {{ background: #111; border: 1px solid #444; border-radius: 15px; padding: 10px; text-align: center; }}
        </style>
        <div class="marquee-container"><div class="marquee-text">{m_txt}</div></div>
    """, unsafe_allow_html=True)
    return m_bg, m_title, m_subtitle, m_desc1, m_desc2, m_desc3, lb_title_1, lb_title_2, m_txt, m_spd, m_mode

# --- 2. 資料庫核心 ---
def init_db():
    with sqlite3.connect('poker_data.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS Members (pf_id TEXT PRIMARY KEY, name TEXT, xp REAL DEFAULT 0, xp_temp REAL DEFAULT 0, role TEXT DEFAULT "玩家", last_checkin TEXT, phone TEXT, password TEXT, ban_until TEXT, vip_level INTEGER DEFAULT 0, vip_expiry TEXT, vip_points REAL DEFAULT 0, join_date TEXT)')
        
        try:
            c.execute('ALTER TABLE Members ADD COLUMN vip_level INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Members ADD COLUMN vip_expiry TEXT')
        except: pass
        try:
            c.execute('ALTER TABLE Members ADD COLUMN vip_points REAL DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Members ADD COLUMN join_date TEXT DEFAULT "' + datetime.now().strftime("%Y-%m-%d") + '"')
        except: pass

        c.execute('''CREATE TABLE IF NOT EXISTS Missions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, reward_xp INTEGER, type TEXT, target_criteria TEXT, target_value INTEGER, status TEXT DEFAULT "Active", reward_item TEXT, required_vip_level INTEGER DEFAULT 0, required_rank_level INTEGER DEFAULT 0, time_limit_months INTEGER DEFAULT 0, recurring_months INTEGER DEFAULT 0)''')
        
        try:
            c.execute('ALTER TABLE Missions ADD COLUMN reward_item TEXT')
        except: pass
        try:
            c.execute('ALTER TABLE Missions ADD COLUMN required_vip_level INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Missions ADD COLUMN required_rank_level INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Missions ADD COLUMN time_limit_months INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Missions ADD COLUMN recurring_months INTEGER DEFAULT 0')
        except: pass

        c.execute('CREATE TABLE IF NOT EXISTS Mission_Logs (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, mission_id INTEGER, claim_time DATETIME)')
        c.execute('CREATE TABLE IF NOT EXISTS Game_Transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, game_type TEXT, action_type TEXT, amount INTEGER, timestamp DATETIME)')
        
        c.execute('CREATE TABLE IF NOT EXISTS Inventory (item_name TEXT PRIMARY KEY, stock INTEGER DEFAULT 0, item_value INTEGER DEFAULT 0, weight REAL DEFAULT 10.0, img_url TEXT, min_xp INTEGER DEFAULT 0, status TEXT DEFAULT "上架中", expiry_type TEXT DEFAULT "無期限", expiry_val TEXT DEFAULT "", target_market TEXT DEFAULT "Both", mall_price INTEGER DEFAULT 0, mall_min_rank TEXT DEFAULT "無限制", wheel_min_rank TEXT DEFAULT "無限制", vip_price INTEGER DEFAULT 0, vip_card_level INTEGER DEFAULT 0, vip_card_hours INTEGER DEFAULT 0)')
        try:
            c.execute('ALTER TABLE Inventory ADD COLUMN vip_card_level INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Inventory ADD COLUMN vip_card_hours INTEGER DEFAULT 0')
        except: pass
        try:
            c.execute('ALTER TABLE Inventory ADD COLUMN wheel_min_rank TEXT DEFAULT "無限制"')
        except: pass
        try:
            c.execute('ALTER TABLE Inventory ADD COLUMN vip_price INTEGER DEFAULT 0')
        except: pass
        
        c.execute('CREATE TABLE IF NOT EXISTS Prizes (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, prize_name TEXT, status TEXT DEFAULT "待兌換", time DATETIME, expire_at TEXT, source TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS Leaderboard (player_id TEXT PRIMARY KEY, hero_points REAL DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS Monthly_God (player_id TEXT PRIMARY KEY, monthly_points REAL DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS Import_History (filename TEXT PRIMARY KEY, import_time DATETIME)')
        c.execute('CREATE TABLE IF NOT EXISTS System_Settings (config_key TEXT PRIMARY KEY, config_value TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS Staff_Logs (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id TEXT, player_id TEXT, prize_name TEXT, time DATETIME)')
        c.execute('CREATE TABLE IF NOT EXISTS Tournament_Records (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, buy_in INTEGER, rank INTEGER, re_entries INTEGER, payout INTEGER, time DATETIME, filename TEXT, total_discount INTEGER DEFAULT 0, actual_fee INTEGER DEFAULT 0)')
        
        c.execute('CREATE TABLE IF NOT EXISTS Baccarat_Global (id INTEGER PRIMARY KEY, current_shoe_id INTEGER, hand_count INTEGER, history_string TEXT, next_reveal_time TEXT, last_result_json TEXT)')
        try:
            c.execute('ALTER TABLE Baccarat_Global ADD COLUMN last_result_json TEXT')
        except: pass
        if not c.execute("SELECT 1 FROM Baccarat_Global").fetchone():
            c.execute("INSERT INTO Baccarat_Global (id, current_shoe_id, hand_count, history_string, next_reveal_time, last_result_json) VALUES (1, 1, 0, '', ?, '{}')", ((datetime.now()+timedelta(seconds=45)).strftime("%Y-%m-%d %H:%M:%S"),))
        c.execute('CREATE TABLE IF NOT EXISTS Baccarat_Pending_Bets (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, bet_amount INTEGER, bet_target TEXT, bet_time DATETIME)')

        c.execute('CREATE TABLE IF NOT EXISTS Roulette_Global (id INTEGER PRIMARY KEY, history_string TEXT, next_spin_time TEXT, last_result INTEGER)')
        if not c.execute("SELECT 1 FROM Roulette_Global").fetchone():
            c.execute("INSERT INTO Roulette_Global (id, history_string, next_spin_time, last_result) VALUES (1, '', ?, -1)", ((datetime.now()+timedelta(seconds=45)).strftime("%Y-%m-%d %H:%M:%S"),))
        c.execute('CREATE TABLE IF NOT EXISTS Roulette_Pending_Bets (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT, bet_amount INTEGER, bet_target TEXT, bet_time DATETIME)')

        c.execute('CREATE TABLE IF NOT EXISTS Help_Sections (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)')

        vip_init = [
            ('vip_name_1', '銅牌 VIP'), ('vip_name_2', '銀牌 VIP'), ('vip_name_3', '黃金 VIP'), ('vip_name_4', '鑽石 VIP'),
            ('vip_discount_1', '0'), ('vip_discount_2', '0'), ('vip_discount_3', '0'), ('vip_discount_4', '0'),
            ('max_redeem_val', '1000000'), ('max_redeem_daily', '50'), ('min_bet_wheel', '100'), ('status_wheel', 'ON')
        ]
        game_status_init = [('status_mines', 'ON'), ('status_wheel', 'ON'), ('status_blackjack', 'ON'), ('status_baccarat', 'ON'), ('status_roulette', 'ON'), ('leaderboard_title_1', '🎖️ 菁英總榜'), ('leaderboard_title_2', '🔥 月度戰神')]
        
        for k, v in vip_init + game_status_init:
            c.execute("INSERT OR IGNORE INTO System_Settings (config_key, config_value) VALUES (?, ?)", (k, v))
        
        c.execute("INSERT OR IGNORE INTO Members (pf_id, name, role, xp, password) VALUES ('330999', '老闆', '老闆', 999999, 'kenken520')")
        c.execute("UPDATE Members SET password = 'kenken520', role = '老闆' WHERE pf_id = '330999'")
        conn.commit()

# --- Global Helper Functions ---
def get_rank_v2500(pts):
    with sqlite3.connect('poker_data.db') as conn:
        limit_c = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rank_limit_challenger'").fetchone() or ("1000",))[0])
        limit_m = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rank_limit_master'").fetchone() or ("500",))[0])
        limit_d = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rank_limit_diamond'").fetchone() or ("200",))[0])
        limit_p = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rank_limit_platinum'").fetchone() or ("80",))[0])
    
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

def get_game_config(game_key):
    with sqlite3.connect('poker_data.db') as conn:
        min_bet = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key = ?", (f'min_bet_{game_key}',)).fetchone() or ("100",))[0])
        max_bet = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key = ?", (f'max_bet_{game_key}',)).fetchone() or ("10000",))[0])
        status = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = ?", (f'status_{game_key}',)).fetchone() or ("ON",))[0]
    return {}, 0.95, min_bet, max_bet, status

def log_game_transaction_cursor(cursor, player_id, game, action, amount):
    cursor.execute("INSERT INTO Game_Transactions (player_id, game_type, action_type, amount, timestamp) VALUES (?, ?, ?, ?, ?)", (player_id, game, action, amount, datetime.now()))

def check_mission_status(player_id, m_type, criteria, target_val, mission_id):
    with sqlite3.connect('poker_data.db') as conn:
        now = datetime.now()
        met = False; current_val = 0
        m_row = conn.execute("SELECT * FROM Missions WHERE id=?", (mission_id,)).fetchone()
        
        if m_row and m_row[11] > 0: # time_limit_months
            join_date_str = conn.execute("SELECT join_date FROM Members WHERE pf_id=?", (player_id,)).fetchone()[0]
            try:
                jd_clean = str(join_date_str).split('.')[0]
                join_date = datetime.strptime(jd_clean, "%Y-%m-%d")
                if (now - join_date).days > (m_row[11] * 30): return False, False, 0
            except: pass
            
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if m_type == "Weekly": start_time = now - timedelta(days=now.weekday())
        elif m_type == "Monthly": start_time = now.replace(day=1)
        elif m_type == "Season": start_time = datetime(2000, 1, 1) 
        
        last_log = conn.execute("SELECT claim_time FROM Mission_Logs WHERE player_id=? AND mission_id=? ORDER BY claim_time DESC LIMIT 1", (player_id, mission_id)).fetchone()
        claimed = False
        if last_log:
            last_log_str = str(last_log[0]).split('.')[0]
            if m_row[12] > 0: # Recurring months
                try:
                    last_claim = datetime.strptime(last_log_str, "%Y-%m-%d %H:%M:%S")
                    if (now - last_claim).days < (m_row[12] * 30): claimed = True
                except: pass
            else:
                try:
                    if datetime.strptime(last_log_str, "%Y-%m-%d %H:%M:%S") >= start_time: claimed = True
                except: pass

        if criteria == "daily_checkin":
            last_chk = conn.execute("SELECT last_checkin FROM Members WHERE pf_id=?", (player_id,)).fetchone()[0]
            if last_chk and str(last_chk).startswith(now.strftime("%Y-%m-%d")): met = True; current_val = 1
        elif criteria == "daily_win":
            cnt = conn.execute("SELECT COUNT(*) FROM Prizes WHERE player_id=? AND source LIKE 'GameWin-%' AND time >= ?", (player_id, now.strftime("%Y-%m-%d 00:00:00"))).fetchone()[0]
            current_val = min(cnt, target_val); met = cnt >= target_val
        elif criteria == "weekly_play":
            w_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
            cnt = conn.execute("SELECT COUNT(*) FROM Tournament_Records WHERE player_id=? AND time >= ?", (player_id, w_start)).fetchone()[0]
            current_val = cnt; met = cnt >= target_val
        elif criteria == "monthly_days":
            m_start = now.strftime("%Y-%m-01 00:00:00")
            cnt = conn.execute("SELECT COUNT(DISTINCT date(time)) FROM Tournament_Records WHERE player_id=? AND time >= ?", (player_id, m_start)).fetchone()[0]
            current_val = cnt; met = cnt >= target_val
        elif criteria == "rank_level":
            hp = conn.execute("SELECT hero_points FROM Leaderboard WHERE player_id=?", (player_id,)).fetchone()
            pts = hp[0] if hp else 0
            curr_lvl = rank_to_level(get_rank_v2500(pts))
            current_val = curr_lvl; met = curr_lvl >= target_val
        elif criteria == "vip_level":
            curr_vip = conn.execute("SELECT vip_level FROM Members WHERE pf_id=?", (player_id,)).fetchone()[0]
            current_val = curr_vip; met = curr_vip >= target_val
        elif criteria == "vip_duration":
            vip_exp = conn.execute("SELECT vip_expiry FROM Members WHERE pf_id=?", (player_id,)).fetchone()[0]
            if vip_exp:
                try:
                    exp_dt = datetime.strptime(str(vip_exp).split('.')[0], "%Y-%m-%d %H:%M:%S")
                    if exp_dt > now:
                        days = (exp_dt - now).days
                        current_val = days; met = days >= target_val
                except: pass

    return met, claimed, current_val

def get_bacc_state():
    with sqlite3.connect('poker_data.db') as conn:
        state = conn.execute("SELECT * FROM Baccarat_Global WHERE id=1").fetchone()
    return state

def get_roulette_state():
    with sqlite3.connect('poker_data.db') as conn:
        state = conn.execute("SELECT * FROM Roulette_Global WHERE id=1").fetchone()
    return state

def get_vip_rank_int(name):
    with sqlite3.connect('poker_data.db') as conn:
        n1 = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key='vip_name_1'").fetchone() or ("銅牌 VIP",))[0]
        n2 = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key='vip_name_2'").fetchone() or ("銀牌 VIP",))[0]
        n3 = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key='vip_name_3'").fetchone() or ("黃金 VIP",))[0]
        n4 = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key='vip_name_4'").fetchone() or ("鑽石 VIP",))[0]
    if name in n1: return 1, n1
    if name in n2: return 2, n2
    if name in n3: return 3, n3
    if name in n4: return 4, n4
    return 0, ""

def get_vip_discount(level):
    if level <= 0: return 0.0
    with sqlite3.connect('poker_data.db') as conn:
        disc_str = (conn.execute(f"SELECT config_value FROM System_Settings WHERE config_key='vip_discount_{level}'").fetchone() or ("0",))[0]
    try: return float(disc_str)
    except: return 0.0

def log_game_transaction(player_id, game, action, amount):
    with sqlite3.connect('poker_data.db') as tx_conn:
        tx_conn.execute("INSERT INTO Game_Transactions (player_id, game_type, action_type, amount, timestamp) VALUES (?, ?, ?, ?, ?)", (player_id, game, action, amount, datetime.now()))
        tx_conn.commit()

# --- Init ---
init_db()
# [FIXED] Unpack m_spd and m_mode
m_bg, m_title, m_subtitle, m_desc1, m_desc2, m_desc3, lb_title_1, lb_title_2, m_txt, m_spd, m_mode = init_flagship_ui()

# --- Auth ---
if "player_id" not in st.session_state:
    st.session_state.player_id = None
    st.session_state.access_level = "玩家"

try:
    tk = st.query_params.get("token")
    if tk and st.session_state.player_id is None:
        with sqlite3.connect('poker_data.db') as conn:
            u = conn.execute("SELECT role, ban_until FROM Members WHERE pf_id = ?", (str(tk),)).fetchone()
        if u:
            is_banned = False
            if u[1]:
                try:
                    ban_str = str(u[1]).split('.')[0]
                    ban_time = datetime.strptime(ban_str, "%Y-%m-%d %H:%M:%S")
                    if datetime.now() < ban_time: is_banned = True
                except: pass
            if is_banned: st.error(f"🚫 此帳號已被封禁，解封時間：{u[1]}"); st.stop()
            else: st.session_state.player_id = tk; st.session_state.access_level = u[0]
except: pass

with st.sidebar:
    st.title("🛡️ 認證總部")
    cur_id = st.session_state.player_id if st.session_state.player_id else ""
    p_id_input = st.text_input("POKERFANS ID", value=cur_id)
    
    u_chk = None
    if p_id_input:
        with sqlite3.connect('poker_data.db') as conn:
            u_chk = conn.execute("SELECT role, password, ban_until FROM Members WHERE pf_id = ?", (p_id_input,)).fetchone()
            invite_cfg = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'reg_invite_code'").fetchone() or ("888",))[0]
    
    if p_id_input and u_chk:
        ban_msg = ""
        if u_chk[2]:
            try:
                ban_str = str(u_chk[2]).split('.')[0]
                bt = datetime.strptime(ban_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < bt: ban_msg = f"🚫 帳號封禁中 (至 {u_chk[2]})"
            except: pass
        if ban_msg: st.error(ban_msg)
        else:
            login_pw = st.text_input("密碼", type="password", key="sidebar_pw")
            if st.button("登入Pro撲克殿堂"):
                if login_pw == u_chk[1]:
                    st.session_state.player_id = p_id_input; st.session_state.access_level = u_chk[0]; st.query_params["token"] = p_id_input; st.rerun()
                else: st.error("❌ 密碼錯誤")
    elif p_id_input:
        with st.form("reg_sidebar"):
            st.info("⚠️ 首次註冊：系統將自動檢查是否為比賽匯入的 ID。")
            rn = st.text_input("暱稱"); rpw = st.text_input("密碼", type="password"); ri = st.text_input("邀請碼")
            if st.form_submit_button("物理註冊") and ri == invite_cfg:
                v_res, v_msg = validate_nickname(rn)
                if v_res:
                    with sqlite3.connect('poker_data.db') as conn:
                        exist_no_pw = conn.execute("SELECT 1 FROM Members WHERE pf_id=? AND (password IS NULL OR password='')", (p_id_input,)).fetchone()
                        if exist_no_pw:
                             conn.execute("UPDATE Members SET name=?, password=?, role='玩家', join_date=? WHERE pf_id=?", (rn, rpw, datetime.now().strftime("%Y-%m-%d"), p_id_input))
                             st.success("✅ 帳號認領成功！暱稱已更新。")
                        else:
                             try:
                                 conn.execute("INSERT INTO Members (pf_id, name, role, xp, password, join_date) VALUES (?,?,?,?,?,?)", (p_id_input, rn, "玩家", 0, rpw, datetime.now().strftime("%Y-%m-%d")))
                                 st.success("✅ 註冊成功！")
                             except sqlite3.IntegrityError:
                                 st.error("❌ 該 ID 已被註冊且設有密碼。")
                        conn.commit()
                else: st.error(f"❌ {v_msg}")
    if st.session_state.player_id:
        if st.button("🚪 退出王國"): st.session_state.player_id = None; st.query_params.clear(); st.rerun()

if not st.session_state.player_id:
    st.markdown(f"""<div class="welcome-wall"><div class="welcome-title">{m_title}</div><div class="welcome-subtitle">{m_subtitle}</div><div class="lobby-features"><div class="feature-box">{m_desc1}</div><div class="feature-box">{m_desc2}</div><div class="feature-box">{m_desc3}</div></div></div>""", unsafe_allow_html=True); st.stop()

# --- 4. 玩家主介面 ---
conn = sqlite3.connect('poker_data.db')
curr_m = datetime.now().strftime("%m")
t_p = st.tabs(["🪪 排位/VIP", "🎯 任務", "🎮 遊戲大廳", "🛒 商城", "🎒 背包", "🏆 榜單"])

m_active = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'monthly_active'").fetchone() or ("ON",))[0]
nick_cost = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'nickname_cost'").fetchone() or ("500",))[0])

with t_p[0]: # 排位卡
    u_row = pd.read_sql_query("SELECT * FROM Members WHERE pf_id=?", conn, params=(st.session_state.player_id,)).iloc[0]
    h_pts = (conn.execute("SELECT hero_points FROM Leaderboard WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    m_pts = (conn.execute("SELECT monthly_points FROM Monthly_God WHERE player_id=?", (st.session_state.player_id,)).fetchone() or (0,))[0]
    player_rank_title = get_rank_v2500(h_pts)
    
    vip_lvl = u_row.get('vip_level', 0)
    vip_exp = u_row.get('vip_expiry')
    vip_pts = u_row.get('vip_points', 0.0)
    
    vip_badge_html = ""
    if vip_lvl > 0 and vip_exp:
        try:
            exp_str = str(vip_exp).split('.')[0]
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < exp_dt:
                v_name = (conn.execute(f"SELECT config_value FROM System_Settings WHERE config_key='vip_name_{vip_lvl}'").fetchone() or (f"LV.{vip_lvl}",))[0]
                remain = exp_dt - datetime.now()
                hours = remain.days * 24 + remain.seconds // 3600
                vip_badge_html = f'<div class="vip-badge">👑 {v_name} | 剩餘 {hours} 小時</div>'
            else:
                with sqlite3.connect('poker_data.db') as tx_conn:
                    tx_conn.execute("UPDATE Members SET vip_level=0 WHERE pf_id=?", (st.session_state.player_id,)); tx_conn.commit()
                vip_lvl = 0
        except: pass
    
    col_vip, col_rank = st.columns(2)
    with col_vip:
        if 'vip_card_flipped' not in st.session_state: st.session_state.vip_card_flipped = False
        if st.button("💳 翻轉 VIP 卡"): st.session_state.vip_card_flipped = not st.session_state.vip_card_flipped
        v_name_display = "普通會員"
        if vip_lvl > 0:
            v_name_display = (conn.execute(f"SELECT config_value FROM System_Settings WHERE config_key='vip_name_{vip_lvl}'").fetchone() or (f"VIP {vip_lvl}",))[0]
        if not st.session_state.vip_card_flipped:
            st.markdown(f'''<div class="vip-card"><div class="vip-card-title">{v_name_display}</div><div class="vip-card-info">姓名: {u_row['name']}</div><div class="vip-card-info">ID: {u_row['pf_id']}</div><div style="margin-top:20px; font-size:1em;">{vip_badge_html}</div></div>''', unsafe_allow_html=True)
        else:
             st.markdown(f'''<div class="vip-card" style="background:#222; color:#FFD700; border-color:#FFD700;"><h3 style="border-bottom:2px solid #666; padding-bottom:10px;">VIP 權益說明</h3><p>享有商城折扣、專屬任務與空投福利。</p><p>當前 VP 點數: {vip_pts:,.0f}</p><p>請維持活躍以保留尊榮身份。</p></div>''', unsafe_allow_html=True)

    with col_rank:
        if 'rank_card_flipped' not in st.session_state: st.session_state.rank_card_flipped = False
        if st.button("🔄 翻轉排位卡"): st.session_state.rank_card_flipped = not st.session_state.rank_card_flipped
        if not st.session_state.rank_card_flipped:
            e_rk_val = conn.execute("SELECT COUNT(*) + 1 FROM Leaderboard WHERE hero_points > ? AND player_id != '330999'", (h_pts,)).fetchone()[0]
            m_rk_val = conn.execute("SELECT COUNT(*) + 1 FROM Monthly_God WHERE monthly_points > ? AND player_id != '330999'", (m_pts,)).fetchone()[0]
            m_display_rk = f"第 {m_rk_val:,} 名" if m_active == "ON" else "比賽未開啟"
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
            rank_card_desc = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'rank_card_desc'").fetchone() or ("排位與積分規則請見遊戲大廳說明。",))[0]
            st.markdown(f"""<div class="rank-card"><h3 style="color:#FFD700;">📖 系統說明</h3><p style="color:#EEE; margin-top:20px;">{rank_card_desc}</p></div>""", unsafe_allow_html=True)

    if st.button("🎰 幸運簽到"):
        today = datetime.now().strftime("%Y-%m-%d")
        if str(u_row['last_checkin']).startswith(today): st.warning("⚠️ 已簽到")
        else:
            with sqlite3.connect('poker_data.db') as tx_conn:
                tx_conn.execute("UPDATE Members SET xp_temp = xp_temp + 10, last_checkin = ? WHERE pf_id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.player_id))
                tx_conn.commit()
            st.success("✅ 簽到成功！"); time.sleep(1); st.rerun()
    with st.expander("🔐 安全中心：修改密碼"):
        new_pw = st.text_input("輸入新密碼", type="password", key="reset_pw_box")
        if st.button("⚡ 執行鋼印替換") and new_pw:
            with sqlite3.connect('poker_data.db') as tx_conn:
                tx_conn.execute("UPDATE Members SET password = ? WHERE pf_id = ?", (new_pw, st.session_state.player_id))
                tx_conn.commit()
            st.success("✅ 修改成功！")
    with st.expander(f"🏷️ 變更暱稱 ({nick_cost} XP)"):
        new_nick = st.text_input("新暱稱", key="nn")
        if st.button(f"變更"):
            v_res, v_msg = validate_nickname(new_nick)
            if v_res and u_row['xp'] >= nick_cost:
                with sqlite3.connect('poker_data.db') as tx_conn:
                    tx_conn.execute("UPDATE Members SET name = ?, xp = xp - ? WHERE pf_id = ?", (new_nick, nick_cost, st.session_state.player_id))
                    tx_conn.commit()
                st.success("成功"); st.rerun()
            else: st.error(v_msg if not v_res else "XP 不足")

with t_p[1]: # 🎯 任務
    st.subheader("🎯 玩家任務中心")
    missions = pd.read_sql_query("SELECT * FROM Missions WHERE status='Active'", conn)
    for m_type in ["Daily", "Weekly", "Monthly", "Season"]:
        st.markdown(f"### 📅 {m_type}")
        type_missions = missions[missions['type'] == m_type]
        if type_missions.empty: continue
        for _, m in type_missions.iterrows():
            is_met, is_claimed, cur_val = check_mission_status(st.session_state.player_id, m_type, m['target_criteria'], m['target_value'], m['id'])
            reward_txt = f"+{m['reward_xp']} XP"
            if m['reward_item']: reward_txt = f"🎁 {m['reward_item']}"
            recur_txt = ""
            if m['recurring_months'] > 0 and is_claimed: recur_txt = f"(冷卻中: {m['recurring_months']} 個月後可再次領取)"
            col_m1, col_m2 = st.columns([8, 2])
            with col_m1:
                st.markdown(f"""<div class="mission-card"><div><div class="mission-title">{m['title']} {recur_txt}</div><div class="mission-desc">{m['description']} (進度: {cur_val}/{m['target_value']})</div></div><div class="mission-reward">{reward_txt}</div></div>""", unsafe_allow_html=True)
            with col_m2:
                if is_claimed: st.button("✅ 已完成", key=f"btn_claimed_{m['id']}", disabled=True)
                elif is_met:
                    if st.button("🎁 領取獎勵", key=f"btn_claim_{m['id']}"):
                        with sqlite3.connect('poker_data.db') as tx_conn:
                            if m['reward_xp'] > 0: tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (m['reward_xp'], st.session_state.player_id))
                            if m['reward_item']:
                                 chk_stock = tx_conn.execute("SELECT stock FROM Inventory WHERE item_name=?", (m['reward_item'],)).fetchone()
                                 if chk_stock and chk_stock[0] > 0:
                                     tx_conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (m['reward_item'],))
                                     tx_conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '待兌換', ?, ?, '任務獎勵')", (st.session_state.player_id, m['reward_item'], datetime.now(), "無期限"))
                                 else: st.error("獎品庫存不足，請聯繫管理員"); st.stop()
                            tx_conn.execute("INSERT INTO Mission_Logs (player_id, mission_id, claim_time) VALUES (?, ?, ?)", (st.session_state.player_id, m['id'], datetime.now()))
                            tx_conn.commit()
                        st.balloons(); st.rerun()
                else: st.button("🔒 未達成", key=f"btn_locked_{m['id']}", disabled=True)

with t_p[2]: # 🎮 遊戲大廳
    st.markdown(f'<div class="xp-bar">💰 當前餘額: {u_row["xp"]:,} XP</div>', unsafe_allow_html=True)
    if 'current_game' not in st.session_state: st.session_state.current_game = 'lobby'
    
    if st.session_state.current_game == 'lobby':
        st.subheader("🎮 撲洛遊戲大廳")
        s_mines = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'status_mines'").fetchone() or ("ON",))[0]
        s_wheel = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'status_wheel'").fetchone() or ("ON",))[0]
        s_bj = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'status_blackjack'").fetchone() or ("ON",))[0]
        s_bacc = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'status_baccarat'").fetchone() or ("ON",))[0]
        s_roulette = (conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'status_roulette'").fetchone() or ("ON",))[0]

        # [LOCKED] Layout: Top 3, Bottom 2
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

        # [LOCKED] Mines Logic (Combinatorics)
        if st.session_state.current_game == 'mines':
            st.subheader("💣 撲洛掃雷")
            if 'mines_active' not in st.session_state: st.session_state.mines_active = False
            if 'mines_game_over' not in st.session_state: st.session_state.mines_game_over = False
            if 'mines_grid' not in st.session_state: st.session_state.mines_grid = []
            if 'mines_revealed' not in st.session_state: st.session_state.mines_revealed = []
            if 'mines_multiplier' not in st.session_state: st.session_state.mines_multiplier = 1.0
            if 'mines_bet_amt' not in st.session_state: st.session_state.mines_bet_amt = 0
            if 'mines_size' not in st.session_state: st.session_state.mines_size = 5

            c_grid, c_bet, c_mines = st.columns(3)
            grid_opt = c_grid.selectbox("選擇戰場", ["5x5 (25格)"], disabled=st.session_state.mines_active)
            mine_bet = c_bet.number_input("投入 XP", 100, 10000, 100, disabled=st.session_state.mines_active)
            mine_count = c_mines.slider("地雷數量", 1, 24, 3, disabled=st.session_state.mines_active)
            
            if st.session_state.mines_active:
                cur_win = int(st.session_state.mines_bet_amt * st.session_state.mines_multiplier)
                st.info(f"🔥 當前倍率: {st.session_state.mines_multiplier:.2f}x | 💰 預期獲利: {cur_win} XP")

            if not st.session_state.mines_active and not st.session_state.mines_game_over:
                if st.button("🚀 開始"):
                     if u_row['xp']>=mine_bet:
                         with sqlite3.connect('poker_data.db') as tx_conn:
                             tx_conn.execute("UPDATE Members SET xp=xp-? WHERE pf_id=?", (mine_bet, st.session_state.player_id)); tx_conn.commit()
                         
                         st.session_state.mines_active=True
                         st.session_state.mines_game_over=False
                         st.session_state.mines_grid=[0]*(25-mine_count)+[1]*mine_count; random.shuffle(st.session_state.mines_grid)
                         st.session_state.mines_revealed=[False]*25
                         st.session_state.mines_multiplier=1.0 
                         st.session_state.mines_bet_amt=mine_bet
                         st.rerun()
                     else: st.error("XP 不足")
            
            cols = st.columns(5)
            if len(st.session_state.mines_revealed) == 25: 
                for i in range(25):
                    with cols[i%5]:
                        if st.session_state.mines_revealed[i]:
                            if st.session_state.mines_grid[i] == 1: st.error("💥")
                            else: st.success("💎")
                        else:
                            if not st.session_state.mines_game_over and st.session_state.mines_active:
                                if st.button("❓", key=f"m_{i}"):
                                    st.session_state.mines_revealed[i]=True
                                    if st.session_state.mines_grid[i]: 
                                        st.session_state.mines_active=False
                                        st.session_state.mines_game_over=True
                                        st.session_state.mines_revealed = [True]*25
                                        st.rerun()
                                    else: 
                                        n_revealed = sum(1 for x in range(25) if st.session_state.mines_revealed[x] and st.session_state.mines_grid[x]==0)
                                        try:
                                            total_comb = math.comb(25, n_revealed)
                                            safe_comb = math.comb(25 - mine_count, n_revealed)
                                            if safe_comb > 0:
                                                st.session_state.mines_multiplier = 0.97 * (total_comb / safe_comb)
                                        except: pass
                                        st.rerun()
                            else: st.button("🔒", key=f"lk_{i}", disabled=True)
            
            if st.session_state.mines_game_over:
                st.error("💥 任務失敗！")
                if st.button("🔄 再來一局"): 
                     st.session_state.mines_game_over=False; st.session_state.mines_active=False; st.rerun()
            elif st.session_state.mines_active:
                if st.button("💰 結算領取 (Cashout)"):
                    win = int(st.session_state.mines_bet_amt * st.session_state.mines_multiplier)
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute("UPDATE Members SET xp=xp+? WHERE pf_id=?", (win, st.session_state.player_id)); tx_conn.commit()
                    st.session_state.mines_active=False; st.balloons(); st.success(f"贏得 {win} XP"); st.rerun()

        # [LOCKED] Wheel Logic
        elif st.session_state.current_game == 'wheel':
             st.subheader("🎡 撲洛幸運大轉盤 (小瑪莉)")
             
             wheel_cost = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key = 'min_bet_wheel'").fetchone() or ("100",))[0])
             st.info(f"消耗: {wheel_cost} XP / 次")
             
             p_lvl = rank_to_level(player_rank_title)
             all_items = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0 AND target_market IN ('Wheel','Both')", conn)
             valid_items = []
             for _, item in all_items.iterrows():
                 if rank_to_level(item.get('wheel_min_rank', '無限制')) <= p_lvl:
                     valid_items.append(item.to_dict())
             
             while len(valid_items) < 8:
                 valid_items.append({"item_name": "銘謝惠顧", "item_value": 0, "img_url": "", "weight": 50})
             
             display_items = valid_items[:8]
             
             grid_html = "<div class='lm-grid'>"
             for idx, item in enumerate(display_items):
                 active_cls = "lm-active" if st.session_state.get('lm_idx') == idx else ""
                 img_tag = f"<img src='{item['img_url']}' class='lm-img'>" if item.get('img_url') else ""
                 grid_html += f"<div class='lm-cell {active_cls}'>{img_tag}<div>{item['item_name']}</div></div>"
             grid_html += "</div>"
             
             wheel_placeholder = st.empty()
             wheel_placeholder.markdown(grid_html, unsafe_allow_html=True)
             
             if st.button("🚀 啟動"):
                 if u_row['xp'] >= wheel_cost:
                     if not valid_items: st.error("獎池目前沒有適合您排位的獎品"); st.stop()
                     
                     with sqlite3.connect('poker_data.db') as tx_conn:
                         tx_conn.execute("UPDATE Members SET xp=xp-? WHERE pf_id=?", (wheel_cost, st.session_state.player_id))
                         
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
                                 wheel_placeholder.markdown(temp_html, unsafe_allow_html=True)
                                 time.sleep(0.1)
                         
                         st.session_state.lm_idx = win_idx
                         final_html = "<div class='lm-grid'>"
                         for dx, ditem in enumerate(display_items):
                             ac = "lm-active" if win_idx == dx else ""
                             it = f"<img src='{ditem.get('img_url','')}' class='lm-img'>" if ditem.get('img_url') else ""
                             final_html += f"<div class='lm-cell {ac}'>{it}<div>{ditem['item_name']}</div></div>"
                         final_html += "</div>"
                         wheel_placeholder.markdown(final_html, unsafe_allow_html=True)

                         if win_item['item_name'] != "銘謝惠顧":
                             tx_conn.execute("UPDATE Inventory SET stock=stock-1 WHERE item_name=?", (win_item['item_name'],))
                             tx_conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?,?,'待兌換',?,?,'Wheel')", (st.session_state.player_id, win_item['item_name'], datetime.now(), "無期限"))
                             tx_conn.commit()
                             st.success(f"恭喜獲得: {win_item['item_name']}")
                             st.balloons()
                         else:
                             tx_conn.commit()
                             st.info("銘謝惠顧，下次好運！")
                 else: st.error("XP 不足")
        
        # [LOCKED] Blackjack Logic
        elif st.session_state.current_game == 'blackjack':
            st.subheader("♠️ 21點")
            if 'bj_active' not in st.session_state: st.session_state.bj_active = False
            if 'bj_game_over' not in st.session_state: st.session_state.bj_game_over = False

            if not st.session_state.bj_active:
                bet = st.number_input("下注 XP", 100, 10000, 100)
                if st.button("🃏 發牌"):
                    if u_row['xp']>=bet:
                        with sqlite3.connect('poker_data.db') as tx_conn:
                            tx_conn.execute("UPDATE Members SET xp=xp-? WHERE pf_id=?", (bet, st.session_state.player_id)); tx_conn.commit()
                        st.session_state.bj_active=True; st.session_state.bj_game_over = False; st.session_state.bj_bet=bet
                        deck=[2,3,4,5,6,7,8,9,10,10,10,10,11]*4; random.shuffle(deck)
                        st.session_state.bj_deck=deck
                        st.session_state.bj_p=[deck.pop(),deck.pop()]
                        st.session_state.bj_d=[deck.pop(),deck.pop()]
                        st.rerun()
            else:
                def hand_val(h):
                    v = 0; aces = 0
                    for r in h:
                        if isinstance(r, int): v+=r
                        elif r in ['J','Q','K']: v+=10
                        elif r == 'A': v+=11; aces+=1
                    while v > 21 and aces: v-=10; aces-=1
                    return v

                p_val = hand_val(st.session_state.bj_p)
                d_val = hand_val(st.session_state.bj_d) if st.session_state.bj_game_over else hand_val([st.session_state.bj_d[0]])
                
                def render_bj_card(c): return f"<div class='bj-card {'suit-red' if c[1] in ['♥','♦'] else 'suit-black'}'>{c[0]}<br>{c[1]}</div>"
                
                d_html = "".join([f"<div class='bj-card'>{c}</div>" for c in st.session_state.bj_d]) if st.session_state.bj_game_over else f"<div class='bj-card'>{st.session_state.bj_d[0]}</div><div class='bj-card'>?</div>"
                p_html = "".join([f"<div class='bj-card'>{c}</div>" for c in st.session_state.bj_p])
                
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
                             with sqlite3.connect('poker_data.db') as tx_conn:
                                 tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (win_amt, st.session_state.player_id))
                                 tx_conn.commit()
                             st.session_state.bj_paid_flag = True
                         st.success(f"恭喜！您贏了 {win_amt} XP！"); st.balloons()
                    else: st.error(f"結果: {msg}")
                        
                    if st.button("🔄 再玩一局"):
                        st.session_state.bj_active = False
                        if 'bj_paid_flag' in st.session_state: del st.session_state.bj_paid_flag
                        st.rerun()

        if st.session_state.current_game == 'roulette':
            st.subheader("🔴 俄羅斯輪盤 (Roulette)")
            
            state = get_roulette_state()
            hist_str = state[1] if state[1] else ""
            hist_list = hist_str.split(',') if hist_str else []
            
            h_html = "<div class='roulette-history-bar'>"
            for h in hist_list:
                if h:
                    n = int(h)
                    c = "#D40000" if n in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else ("#008000" if n == 0 else "#111")
                    h_html += f"<div class='hist-ball' style='background-color:{c}'>{n}</div>"
            h_html += "</div>"
            st.markdown(h_html, unsafe_allow_html=True)

            if 'roulette_bets' not in st.session_state: st.session_state.roulette_bets = {} 
            if 'roulette_chips' not in st.session_state: st.session_state.roulette_chips = 100

            st.write("🪙 選擇籌碼")
            chips = [100, 500, 1000, 5000, 10000]
            cc = st.columns(len(chips))
            for i, c in enumerate(chips):
                if cc[i].button(f"{c}", key=f"rc_{c}"): st.session_state.roulette_chips = c
            
            st.write(f"🎲 當前籌碼: {st.session_state.roulette_chips} | 點擊下方按鈕下注")
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

            total_bet = sum(st.session_state.roulette_bets.values())
            st.info(f"💰 目前總下注: {total_bet} XP")
            
            with st.expander("查看詳細注單"):
                if st.session_state.roulette_bets:
                    st.table(pd.DataFrame(list(st.session_state.roulette_bets.items()), columns=["下注目標", "金額"]))
                else: st.write("尚無下注")
            
            c_act1, c_act2 = st.columns(2)
            if c_act1.button("🗑️ 清空"): st.session_state.roulette_bets = {}; st.rerun()
            
            if c_act2.button("🚀 旋轉輪盤 (SPIN)", type="primary"):
                if total_bet > 0 and u_row['xp'] >= total_bet:
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute("UPDATE Members SET xp = xp - ? WHERE pf_id = ?", (total_bet, st.session_state.player_id))
                        rtp = float((tx_conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rtp_roulette'").fetchone() or ("0.95",))[0])
                        
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
                            tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (total_win, st.session_state.player_id))
                            tx_conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '自動入帳', ?, ?, ?)", (st.session_state.player_id, f"{total_win} XP", datetime.now(), "無期限", "GameWin-Roulette"))
                        
                        new_hist_list = [str(final_num)] + hist_list[:39] 
                        new_hist_str = ",".join(new_hist_list)
                        tx_conn.execute("UPDATE Roulette_Global SET history_string=? WHERE id=1", (new_hist_str,))
                        
                        log_game_transaction_cursor(tx_conn.cursor(), st.session_state.player_id, 'roulette', 'BET', total_bet)
                        if total_win > 0: log_game_transaction_cursor(tx_conn.cursor(), st.session_state.player_id, 'roulette', 'WIN', total_win)
                        
                        tx_conn.commit()
                        
                    placeholder = st.empty()
                    placeholder.markdown('<div class="roulette-wheel-anim">🎲</div>', unsafe_allow_html=True)
                    time.sleep(2)
                    res_c = "#D40000" if final_num in red_nums else ("#008000" if final_num==0 else "#111")
                    placeholder.markdown(f"<div style='text-align:center; font-size:4em; color:{res_c}; font-weight:bold;'>{final_num}</div>", unsafe_allow_html=True)
                    
                    if total_win > 0: st.success(f"恭喜贏得 {total_win} XP！"); st.balloons()
                    else: st.error("未中獎")
                    
                    st.session_state.roulette_bets = {}
                    time.sleep(2); st.rerun()

                else: st.error("XP 不足或未下注")

        # [LOCKED] Baccarat Logic
        elif st.session_state.current_game == 'baccarat':
            st.subheader("🏛️ 皇家百家樂 (Royal Baccarat)")
            
            if 'bacc_chips' not in st.session_state: st.session_state.bacc_chips = 100
            if 'bacc_bets' not in st.session_state: st.session_state.bacc_bets = {"P":0, "B":0, "T":0, "PP":0, "BP":0}
            
            # 路單 (Bead Plate)
            state = get_bacc_state()
            hist_str = state[3] if state[3] else ""
            hist_list = hist_str.split(',') if hist_str else []
            hand_count = state[2]

            st.markdown("#### 📜 牌路 (Bead Plate)")
            bead_html = "<div class='bead-plate'>"
            for h in hist_list:
                if h:
                    c = "bead-P" if h=='P' else ("bead-B" if h=='B' else "bead-T")
                    bead_html += f"<div class='bead {c}'>{h}</div>"
            bead_html += "</div>"
            st.markdown(bead_html, unsafe_allow_html=True)
            st.caption(f"目前第 {hand_count} 手 (60手後自動洗牌)")

            # Chip Selector
            st.write("#### 🪙 選擇籌碼")
            chips = [100, 500, 1000, 5000, 10000]
            chip_cols = st.columns(len(chips))
            for i, chip in enumerate(chips):
                with chip_cols[i]:
                    if st.button(f"{chip}", key=f"chip_{chip}"):
                        st.session_state.bacc_chips = chip
            st.info(f"當前選定籌碼: {st.session_state.bacc_chips}")

            # Betting Table
            c1, c2, c3, c4, c5 = st.columns(5)
            
            def add_bet(target):
                st.session_state.bacc_bets[target] += st.session_state.bacc_chips
            
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
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        rtp = float((tx_conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rtp_baccarat'").fetchone() or ("0.95",))[0])
                        deck = [1,2,3,4,5,6,7,8,9,10,11,12,13] * 8; random.shuffle(deck)
                        
                        # RTP Logic Loop
                        for _ in range(10):
                            p_hand = [deck.pop(), deck.pop()]; b_hand = [deck.pop(), deck.pop()]
                            def get_val(h): return sum([0 if c>=10 else c for c in h]) % 10
                            
                            if get_val(p_hand) < 8 and get_val(b_hand) < 8:
                                if get_val(p_hand) <= 5: p_hand.append(deck.pop())
                                if get_val(b_hand) <= 5: b_hand.append(deck.pop()) 
                            
                            p_val = get_val(p_hand); b_val = get_val(b_hand)
                            winner = "T"
                            if p_val > b_val: winner = "P"
                            elif b_val > p_val: winner = "B"
                            
                            is_pp = p_hand[0] == p_hand[1]
                            is_bp = b_hand[0] == b_hand[1]

                            # Calc Potential Win
                            pot_win = 0
                            if winner == "P": pot_win += st.session_state.bacc_bets['P'] * 2
                            if winner == "B": pot_win += int(st.session_state.bacc_bets['B'] * 1.95)
                            if winner == "T": pot_win += st.session_state.bacc_bets['T'] * 9
                            if is_pp: pot_win += st.session_state.bacc_bets['PP'] * 12
                            if is_bp: pot_win += st.session_state.bacc_bets['BP'] * 12
                            
                            if winner == "T": # Return bets on P/B if Tie
                                pot_win += st.session_state.bacc_bets['P']
                                pot_win += st.session_state.bacc_bets['B']
                            
                            if random.random() > rtp and pot_win > total_bet: 
                                continue # Try to kill
                            else: 
                                break # Accept result
                        
                        # Execute
                        tx_conn.execute("UPDATE Members SET xp = xp - ? WHERE pf_id = ?", (total_bet, st.session_state.player_id))
                        log_game_transaction_cursor(tx_conn.cursor(), st.session_state.player_id, 'baccarat', 'BET', total_bet)
                        
                        if pot_win > 0:
                            tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (pot_win, st.session_state.player_id))
                            tx_conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '自動入帳', ?, ?, ?)", (st.session_state.player_id, f"{pot_win} XP", datetime.now(), "無期限", "GameWin-bacc"))
                            log_game_transaction_cursor(tx_conn.cursor(), st.session_state.player_id, 'baccarat', 'WIN', pot_win)
                        
                        tx_conn.commit()

                        # Animation
                        ph = st.empty(); bh = st.empty()
                        
                        def render_card(val):
                             s = random.choice(['♠', '♣', '♥', '♦'])
                             c = "red" if s in ['♥', '♦'] else "black"
                             d = {1:'A',11:'J',12:'Q',13:'K'}.get(val, str(val))
                             return f"<div class='bacc-card {c}'>{d}<br>{s}</div>"

                        # Reveal Player
                        p_html = ""
                        for card in p_hand:
                            p_html += render_card(card)
                            ph.markdown(f"<div style='text-align:center'><h3>🔵 閒家</h3><div>{p_html}</div></div>", unsafe_allow_html=True)
                            time.sleep(0.5)
                        
                        # Reveal Banker
                        b_html = ""
                        for card in b_hand:
                            b_html += render_card(card)
                            bh.markdown(f"<div style='text-align:center'><h3>🔴 莊家</h3><div>{b_html}</div></div>", unsafe_allow_html=True)
                            time.sleep(0.5)

                        res_msg = f"結果: {winner} ({p_val} vs {b_val})"
                        if pot_win > total_bet: st.success(f"贏得 {pot_win} XP! {res_msg}"); st.balloons()
                        elif pot_win == total_bet: st.info(f"退回本金 {res_msg}")
                        else: st.error(f"莊家通吃 {res_msg}")
                        
                        # Update History
                        new_hist = state[3] + "," + winner if state[3] else winner
                        new_count = hand_count + 1
                        if new_count >= 60: 
                            new_hist = ""; new_count = 0; st.toast("🔄 洗牌中...")
                        
                        with sqlite3.connect('poker_data.db') as up_conn:
                            up_conn.execute("UPDATE Baccarat_Global SET hand_count=?, history_string=? WHERE id=1", (new_count, new_hist))
                            up_conn.commit()

                        st.session_state.bacc_bets = {k:0 for k in st.session_state.bacc_bets}
                        time.sleep(2); st.rerun()

                else: st.error("XP 不足或未下注")

with t_p[3]: # 商城
    st.subheader("🛒 商城")
    srt = st.radio("排序", ["市價高>低", "市價低>高"], horizontal=True, key="m_sort")
    asc = True if "低>高" in srt else False
    items = pd.read_sql_query("SELECT * FROM Inventory WHERE stock > 0 AND status='上架中' AND (target_market='Mall' OR target_market='Both')", conn)
    if not items.empty:
        items = items.sort_values(by='item_value', ascending=asc)
        ic = st.columns(3)
        for i, r in items.reset_index(drop=True).iterrows():
            with ic[i%3]:
                # --- 【物理新增】：VIP 折扣邏輯 ---
                discount = get_vip_discount(vip_lvl)
                
                # --- 【物理新增】：雙幣顯示與折扣計算 ---
                final_xp_price = int(r['mall_price'] * (1 - discount/100.0))
                vip_price_val = r.get('vip_price', 0)
                
                # 顯示原價與折扣價 (如果有的話)
                xp_display = f"⚡{final_xp_price:,} XP"
                if discount > 0:
                    xp_display += f" <span style='font-size:0.8em;color:#AAA;text-decoration:line-through;'>({r['mall_price']:,})</span> <span style='font-size:0.8em;color:#FFD700;'>(-{discount}%)</span>"
                
                vp_display = ""
                if vip_price_val > 0:
                    vp_display = f"<div class='vip-price'>💎 {vip_price_val:,} VP</div>"

                limit_txt = f"🔒 需 {r.get('mall_min_rank', '無限制')}" if r.get('mall_min_rank') != '無限制' else "✅ 無限制"
                
                # [FIXED] Mall Card HTML Structure - Properly closed div, No item_value
                img_html = f"<img src='{r['img_url']}' class='mall-img'>" if r['img_url'] else ""
                
                st.markdown(f'''<div class="mall-card">{img_html}<div><p>{r['item_name']}</p><p class="mall-price">{xp_display}</p>{vp_display}</div><p style="color:#AAA;font-size:0.8em;margin-top:5px;">{limit_txt}</p></div>''', unsafe_allow_html=True)
                
                p_lvl = rank_to_level(player_rank_title); r_lvl = rank_to_level(r.get('mall_min_rank', '無限制'))
                
                if p_lvl >= r_lvl:
                    c_buy1, c_buy2 = st.columns(2)
                    if c_buy1.button(f"XP 購買", key=f"bxp_{r['item_name']}"):
                        if u_row['xp'] >= final_xp_price:
                            conn.execute("UPDATE Members SET xp = xp - ? WHERE pf_id = ?", (final_xp_price, st.session_state.player_id))
                            conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (r['item_name'],))
                            conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '待兌換', ?, ?, '商城購買')", (st.session_state.player_id, r['item_name'], datetime.now(), "無期限"))
                            conn.commit(); st.success("購買成功"); st.rerun()
                        else: st.error("XP 不足")
                    
                    if vip_price_val > 0:
                        if c_buy2.button(f"VP 購買", key=f"bvp_{r['item_name']}"):
                             if u_row.get('vip_points', 0) >= vip_price_val:
                                 conn.execute("UPDATE Members SET vip_points = vip_points - ? WHERE pf_id = ?", (vip_price_val, st.session_state.player_id))
                                 conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (r['item_name'],))
                                 conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '待兌換', ?, ?, '商城(VP)')", (st.session_state.player_id, r['item_name'], datetime.now(), "無期限"))
                                 conn.commit(); st.success("VP 購買成功"); st.rerun()
                             else: st.error("VP 不足")
                else: st.button(f"🔒 需 {r['mall_min_rank']}", disabled=True, key=f"lk_{r['item_name']}")

with t_p[4]: # 背包
    st.subheader("🎒 背包")
    prizes = pd.read_sql_query("SELECT * FROM Prizes WHERE player_id=? AND source NOT LIKE 'GameWin-%' ORDER BY id DESC", conn, params=(st.session_state.player_id,))
    h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 3, 2, 2])
    h1.markdown("**選取**"); h2.markdown("**ID**"); h3.markdown("**來源**"); h4.markdown("**物品**"); h5.markdown("**狀態**"); h6.markdown("**效期**")
    st.write("---")
    sel = []
    for _, r in prizes.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 3, 2, 2])
        if c1.checkbox("", key=f"del_{r['id']}"): sel.append(r['id'])
        c2.write(str(r['id'])); c3.write(r['source']); c4.write(r['prize_name']); c5.write(r['status']); c6.write(r.get('expire_at', '無期限'))
    if sel and st.button("🗑️ 刪除選取"):
        with sqlite3.connect('poker_data.db') as tx_conn:
            for i in sel: tx_conn.execute("DELETE FROM Prizes WHERE id=?", (i,))
            tx_conn.commit(); st.success("已刪除"); st.rerun()

with t_p[5]: # 榜單
    ldf1, ldf2 = st.columns(2)
    with ldf1:
        st.markdown(f"<div class='glory-title'>{lb_title_1}</div>", unsafe_allow_html=True)
        # [FIXED] Full List Vertical
        df1 = pd.read_sql_query("SELECT L.player_id, M.name, L.hero_points FROM Leaderboard L JOIN Members M ON L.player_id=M.pf_id WHERE M.role != '老闆' ORDER BY L.hero_points DESC LIMIT 20", conn)
        
        if not df1.empty:
            for i, row in df1.iterrows():
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                
                st.markdown(f"""
                <div class="lb-rank-card {style_class}">
                    <div class="lb-badge">{badge}</div>
                    <div class="lb-info">
                        <div class="lb-name">{row['name']}</div>
                        <div class="lb-id">{row['player_id']}</div>
                    </div>
                    <div class="lb-score">{row['hero_points']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暫無資料")

    with ldf2:
        st.markdown(f"<div class='glory-title'>{lb_title_2}</div>", unsafe_allow_html=True)
        # [FIXED] Full List Vertical
        df2 = pd.read_sql_query("SELECT G.player_id, M.name, G.monthly_points FROM Monthly_God G JOIN Members M ON G.player_id=M.pf_id WHERE M.role != '老闆' ORDER BY G.monthly_points DESC LIMIT 20", conn)
        
        if not df2.empty:
            for i, row in df2.iterrows():
                rank_num = i + 1
                badge = "👑" if rank_num == 1 else ("🥈" if rank_num == 2 else ("🥉" if rank_num == 3 else f"#{rank_num}"))
                style_class = "lb-rank-1" if rank_num == 1 else ("lb-rank-2" if rank_num == 2 else ("lb-rank-3" if rank_num == 3 else "lb-rank-norm"))
                
                st.markdown(f"""
                <div class="lb-rank-card {style_class}">
                    <div class="lb-badge">{badge}</div>
                    <div class="lb-info">
                        <div class="lb-name">{row['name']}</div>
                        <div class="lb-id">{row['player_id']}</div>
                    </div>
                    <div class="lb-score">{row['monthly_points']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暫無資料")

# --- 5. 指揮部 (Admin) ---
if st.session_state.access_level in ["老闆", "店長", "員工"]:
    st.write("---"); st.header("⚙️ 指揮部")
    user_role = st.session_state.access_level
    
    tabs = st.tabs(["💰 櫃台與物資", "👥 人員與空投", "📊 賽事與數據", "🛠️ 系統與維護"])
    
    with tabs[0]: 
        st.subheader("🛂 櫃台核銷")
        target = st.text_input("玩家 ID")
        if target:
            pendings = pd.read_sql_query("SELECT P.id, P.prize_name, I.item_value, I.vip_card_level, I.vip_card_hours FROM Prizes P LEFT JOIN Inventory I ON P.prize_name = I.item_name WHERE P.player_id=? AND P.status='待兌換'", conn, params=(target,))
            if not pendings.empty:
                st.table(pendings)
                redeem_id = st.selectbox("選擇核銷項目 ID", pendings['id'].tolist())
                max_val = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='max_redeem_val'").fetchone() or ("1000000",))[0])
                selected_item = pendings[pendings['id'] == redeem_id].iloc[0]
                item_val = selected_item.get('item_value', 0) or 0
                
                if user_role != "老闆" and item_val > max_val:
                    st.error(f"❌ 此物品價值 ({item_val}) 超過您的核銷權限 ({max_val})，請聯繫老闆。")
                else:
                    if st.button("確認核銷"):
                        if selected_item['vip_card_hours'] > 0:
                            with sqlite3.connect('poker_data.db') as tx_conn:
                                curr_v = tx_conn.execute("SELECT vip_level, vip_expiry FROM Members WHERE pf_id=?", (target,)).fetchone()
                                c_lvl, c_exp = curr_v[0], curr_v[1]
                                now = datetime.now(); start_time = now
                                if c_lvl == selected_item['vip_card_level'] and c_exp:
                                    try:
                                        exp_dt = datetime.strptime(str(c_exp).split('.')[0], "%Y-%m-%d %H:%M:%S")
                                        if exp_dt > now: start_time = exp_dt
                                    except: pass
                                new_exp = (start_time + timedelta(hours=selected_item['vip_card_hours'])).strftime("%Y-%m-%d %H:%M:%S")
                                tx_conn.execute("UPDATE Members SET vip_level=?, vip_expiry=? WHERE pf_id=?", (selected_item['vip_card_level'], new_exp, target))
                                tx_conn.commit()
                            st.success(f"VIP 已自動開通，效期至 {new_exp}")
                        
                        with sqlite3.connect('poker_data.db') as tx_conn:
                            tx_conn.execute("UPDATE Prizes SET status='已核銷' WHERE id=?", (redeem_id,))
                            tx_conn.execute("INSERT INTO Staff_Logs (staff_id, player_id, prize_name, time) VALUES (?,?,?,?)", (st.session_state.player_id, target, selected_item['prize_name'], datetime.now()))
                            tx_conn.commit()
                        st.success("核銷完成"); st.rerun()
            else: st.info("該玩家無待核銷物品")
            
            st.write("---"); st.subheader("💰 人工充值")
            xp_add = st.number_input("充值 XP", step=100)
            if st.button("執行充值"):
                with sqlite3.connect('poker_data.db') as tx_conn:
                    tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (xp_add, target)); tx_conn.commit()
                st.success("已充值")
            
            st.write("---"); st.subheader("📜 歷史核銷紀錄")
            d1 = st.date_input("開始日期"); d2 = st.date_input("結束日期")
            if st.button("查詢紀錄"):
                 q_start = d1.strftime("%Y-%m-%d 00:00:00"); q_end = d2.strftime("%Y-%m-%d 23:59:59")
                 logs = pd.read_sql_query("SELECT * FROM Staff_Logs WHERE time BETWEEN ? AND ?", conn, params=(q_start, q_end))
                 st.dataframe(logs)
                 if user_role == "老闆" and not logs.empty:
                     if st.button("⚠️ 刪除此區間紀錄"):
                         with sqlite3.connect('poker_data.db') as tx_conn:
                             tx_conn.execute("DELETE FROM Staff_Logs WHERE time BETWEEN ? AND ?", (q_start, q_end))
                             tx_conn.commit()
                         st.warning("已刪除")

        st.write("---")
        with st.expander("📦 商品上架與管理"):
            with st.form("add_item"):
                n = st.text_input("名稱"); v = st.number_input("市價", 0); s = st.number_input("庫存", 0); w = st.number_input("轉盤權重 (小瑪莉機率)", 0.0, help="數字越大，在小瑪莉機台中被抽中的機率越高"); mp = st.number_input("商城價格 (XP)", 0)
                st.markdown("###### 💎 VIP 權益卡設定")
                is_vip = st.checkbox("是否為 VIP 權益卡?"); v_lvl = st.selectbox("VIP 等級 (1=銅, 2=銀, 3=金, 4=鑽)", [1,2,3,4]) if is_vip else 0; v_hrs = st.number_input("VIP 時數 (小時)", 0) if is_vip else 0
                st.markdown("###### 🛒 上架設定")
                img = st.text_input("圖片 URL"); r_min = st.selectbox("購買排位限制", ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"]); vp_price = st.number_input("VP 價格 (0=不可用VP買)", 0)
                target_m = st.selectbox("上架位置", ["Both", "Mall", "Wheel"])
                if st.form_submit_button("上架"):
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute("INSERT OR REPLACE INTO Inventory (item_name, stock, item_value, weight, target_market, mall_price, vip_card_level, vip_card_hours, img_url, mall_min_rank, vip_price) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (n, s, v, w, target_m, mp, v_lvl, v_hrs, img, r_min, vp_price)); tx_conn.commit()
                    st.success("上架成功")
            
            st.write("📋 架上商品列表 (可編輯/刪除)")
            inv_df = pd.read_sql_query("SELECT * FROM Inventory", conn)
            for _, mm in inv_df.iterrows():
                with st.expander(f"{mm['item_name']} (庫存: {mm['stock']})"):
                    c1, c2, c3, c4 = st.columns(4)
                    new_p = c1.number_input(f"XP售價", value=int(mm['mall_price']), key=f"mm_p_{mm['item_name']}")
                    new_vp = c2.number_input(f"VP售價", value=int(mm.get('vip_price', 0)), key=f"mm_vp_{mm['item_name']}")
                    new_s = c3.number_input(f"庫存", value=mm['stock'], key=f"mm_s_{mm['item_name']}")
                    new_r = c4.selectbox(f"限制", ["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"], index=["無限制", "🥈 白銀 (Silver)", "⬜ 白金 (Platinum)", "💎 鑽石 (Diamond)", "🎖️ 大師 (Master)", "🏆 菁英 (Challenger)"].index(mm.get('mall_min_rank', '無限制')), key=f"mm_r_{mm['item_name']}")
                    
                    c5, c6, c7 = st.columns([2, 1, 1])
                    new_u = c5.text_input("圖片", value=mm['img_url'], key=f"mm_u_{mm['item_name']}")
                    new_st = c6.selectbox("狀態", ["上架中", "下架中"], index=0 if mm['status']=='上架中' else 1, key=f"mm_st_{mm['item_name']}")
                    if c7.button(f"💾 保存變更", key=f"mm_up_{mm['item_name']}"):
                        conn.execute("UPDATE Inventory SET mall_price=?, vip_price=?, stock=?, mall_min_rank=?, img_url=?, status=? WHERE item_name=?", (new_p, new_vp, new_s, new_r, new_u, new_st, mm['item_name'])); conn.commit(); st.success("已更新"); time.sleep(0.5); st.rerun()
                    if st.button("刪除商品", key=f"mm_del_{mm['item_name']}"):
                         with sqlite3.connect('poker_data.db') as tx_conn:
                             tx_conn.execute("DELETE FROM Inventory WHERE item_name=?", (mm['item_name'],)); tx_conn.commit(); st.success("Deleted"); st.rerun()
            
            st.write("---")
            st.subheader("🎡 轉盤獎池與機率管理")
            wheel_items = pd.read_sql_query("SELECT * FROM Inventory WHERE target_market IN ('Wheel', 'Both')", conn)
            total_weight = wheel_items[wheel_items['stock'] > 0]['weight'].sum()
            if not wheel_items.empty:
                for _, item in wheel_items.iterrows():
                    prob = (item['weight'] / total_weight * 100) if total_weight > 0 and item['stock'] > 0 else 0
                    status_emoji = "🟢" if item['stock'] > 0 else "🔴 缺貨"
                    with st.expander(f"{status_emoji} {item['item_name']} (預估機率: {prob:.1f}%)"):
                        c1, c2, c3 = st.columns(3)
                        new_w = c1.number_input(f"權重 (Weight)", value=float(item['weight']), key=f"w_w_{item['item_name']}")
                        new_s = c2.number_input(f"庫存", value=int(item['stock']), key=f"w_s_{item['item_name']}")
                        new_v = c3.number_input(f"顯示價值", value=int(item['item_value']), key=f"w_v_{item['item_name']}")
                        if st.button(f"更新 {item['item_name']}", key=f"btn_w_{item['item_name']}"):
                             conn.execute("UPDATE Inventory SET weight=?, stock=?, item_value=? WHERE item_name=?", (new_w, new_s, new_v, item['item_name']))
                             conn.commit(); st.success("已更新"); time.sleep(0.5); st.rerun()

    with tabs[1]: # 人員與空投
        st.subheader("🔍 查閱與管理")
        q = st.text_input("查詢玩家 ID", key="query_lookup_id_2")
        if q:
            with sqlite3.connect('poker_data.db') as tx_conn:
                mem = tx_conn.execute("SELECT name, xp, xp_temp, role, ban_until, vip_level, vip_expiry, vip_points FROM Members WHERE pf_id=?", (q,)).fetchone()
            if mem:
                st.markdown(f"""
                <div class="lookup-result-box">
                    <h3>👤 {mem[0]} (ID: {q})</h3>
                    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr;">
                        <div><span class="lookup-label">XP 餘額</span><br><span class="lookup-value">{mem[1]:,.0f}</span></div>
                        <div><span class="lookup-label">VIP 點數</span><br><span class="lookup-value">{mem[7]:,.0f}</span></div>
                        <div><span class="lookup-label">角色權限</span><br><span style="color:#FFD700;">{mem[3]}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                total_contribution = conn.execute("SELECT SUM(actual_fee) FROM Tournament_Records WHERE player_id=?", (q,)).fetchone()[0] or 0
                st.markdown(f"**生涯總貢獻 (淨利): {total_contribution:,}**")

                if user_role == "老闆":
                    with st.expander("🚫 封禁管理"):
                        if st.button("❌ 物理刪除玩家"):
                            with sqlite3.connect('poker_data.db') as tx_conn:
                                tx_conn.execute("DELETE FROM Members WHERE pf_id = ?", (q,))
                                tx_conn.execute("DELETE FROM Prizes WHERE player_id = ?", (q,))
                                tx_conn.execute("DELETE FROM Leaderboard WHERE player_id = ?", (q,))
                                tx_conn.execute("DELETE FROM Monthly_God WHERE player_id = ?", (q,))
                                tx_conn.commit()
                            st.error("已刪除"); st.rerun()
                            
                    with st.expander("👮 懲處：扣除玩家 XP"):
                         deduct_xp = st.number_input("扣除數量", min_value=1, value=100, key="deduct_xp_val_2")
                         if st.button("執行扣除", key="btn_deduct_xp_2"):
                             with sqlite3.connect('poker_data.db') as tx_conn:
                                 tx_conn.execute("UPDATE Members SET xp = xp - ? WHERE pf_id = ?", (deduct_xp, q)); tx_conn.commit()
                             st.success("已扣除"); st.rerun()

                with st.expander("🎰 近 20 場遊戲紀錄"):
                    gw = pd.read_sql_query("SELECT source, prize_name, time FROM Prizes WHERE player_id=? AND source LIKE 'GameWin-%' ORDER BY id DESC LIMIT 20", conn, params=(q,))
                    st.table(gw)
                
                with st.expander("🎒 背包庫存"):
                    bp = pd.read_sql_query("SELECT prize_name, status, expire_at FROM Prizes WHERE player_id=? AND status='待兌換' ORDER BY id DESC", conn, params=(q,))
                    st.table(bp)
                
                with st.expander("🏆 參賽紀錄"):
                    tr = pd.read_sql_query("SELECT buy_in, rank, re_entries, payout, time FROM Tournament_Records WHERE player_id=? ORDER BY id DESC LIMIT 20", conn, params=(q,))
                    st.table(tr)

            else: st.error("無此人")

        st.write("---")
        st.subheader("🚀 物資空投")
        target_group = st.selectbox("發送對象", ["單一玩家 ID", "全體玩家", "🏆 菁英", "🎖️ 大師", "💎 鑽石", "⬜ 白金", "🥈 白銀", "VIP 1 (銅)", "VIP 2 (銀)", "VIP 3 (金)", "VIP 4 (鑽)"])
        
        target_ids = []
        if target_group == "單一玩家 ID":
            tid = st.text_input("輸入玩家 ID")
            if tid: target_ids = [tid]
        elif target_group == "全體玩家":
            target_ids = pd.read_sql_query("SELECT pf_id FROM Members", conn)['pf_id'].tolist()
        else:
            sql = ""
            if "菁英" in target_group: sql = "SELECT player_id FROM Leaderboard WHERE hero_points >= 2501" 
            elif "VIP 1" in target_group: sql = "SELECT pf_id FROM Members WHERE vip_level = 1"
            elif "VIP 2" in target_group: sql = "SELECT pf_id FROM Members WHERE vip_level = 2"
            elif "VIP 3" in target_group: sql = "SELECT pf_id FROM Members WHERE vip_level = 3"
            elif "VIP 4" in target_group: sql = "SELECT pf_id FROM Members WHERE vip_level = 4"
            
            if sql: target_ids = pd.read_sql_query(sql, conn).iloc[:,0].tolist()
            
        st.info(f"預計發送對象人數: {len(target_ids)} 人")
        
        c_xp, c_vp, c_it = st.columns(3)
        xp = c_xp.number_input("XP 點數", 0)
        vp = c_vp.number_input("VIP 點數", 0)
        it = c_it.selectbox("禮物 (庫存)", ["無"] + pd.read_sql_query("SELECT item_name FROM Inventory", conn)['item_name'].tolist())
        
        if st.button("確認空投"):
            if not target_ids: st.error("無目標")
            else:
                with sqlite3.connect('poker_data.db') as tx_conn:
                    for t in target_ids:
                        if xp: tx_conn.execute("UPDATE Members SET xp = xp + ? WHERE pf_id = ?", (xp, t))
                        if vp: tx_conn.execute("UPDATE Members SET vip_points = vip_points + ? WHERE pf_id = ?", (vp, t))
                        if it != "無":
                             tx_conn.execute("UPDATE Inventory SET stock = stock - 1 WHERE item_name = ?", (it,))
                             tx_conn.execute("INSERT INTO Prizes (player_id, prize_name, status, time, expire_at, source) VALUES (?, ?, '待兌換', ?, ?, '老闆空投')", (t, it, datetime.now(), "無期限"))
                    tx_conn.commit()
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
                
                # [FIXED] Column strip and check
                df.columns = df.columns.str.strip()
                if 'ID' not in df.columns:
                     st.error(f"錯誤：找不到 'ID' 欄位。偵測到的欄位: {list(df.columns)}")
                     st.stop()
                
                matrix = {1200: (200, 0.75, [2, 1.5, 1]), 3400: (400, 1.5, [5, 4, 3]), 6600: (600, 2.0, [10, 8, 6]), 11000: (1000, 3.0, [20, 15, 10]), 21500: (1500, 5.0, [40, 30, 20])}
                base, p_mult, bonuses = matrix[buy]
                with sqlite3.connect('poker_data.db') as tx_conn:
                    for _, r in df.iterrows():
                        pid = str(r['ID']); raw_name = str(r['Nickname']); name = raw_name[:10] if len(raw_name) > 10 else raw_name
                        exist = tx_conn.execute("SELECT password FROM Members WHERE pf_id=?", (pid,)).fetchone()
                        if not (exist and exist[0]): 
                             tx_conn.execute("INSERT OR REPLACE INTO Members (pf_id, name, xp, role) VALUES (?, ?, COALESCE((SELECT xp FROM Members WHERE pf_id=?), 0), '玩家')", (pid, name, pid))
                        
                        rank = int(r['Rank'])
                        points = base + int(base * (1/rank) * p_mult)
                        if rank <= 3: points = int(points * bonuses[rank-1])
                        
                        tx_conn.execute("INSERT OR REPLACE INTO Leaderboard (player_id, hero_points) VALUES (?, COALESCE((SELECT hero_points FROM Leaderboard WHERE player_id=?), 0) + ?)", (pid, pid, points))
                        tx_conn.execute("INSERT OR REPLACE INTO Monthly_God (player_id, monthly_points) VALUES (?, COALESCE((SELECT monthly_points FROM Monthly_God WHERE player_id=?), 0) + ?)", (pid, pid, points))
                        
                        tx_conn.execute("INSERT INTO Tournament_Records (player_id, buy_in, rank, re_entries, payout, time, filename, actual_fee) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                                        (pid, buy, rank, int(r.get('Re-entry', 0)), 0, datetime.now(), fn, buy))

                    tx_conn.commit()
                st.success("完成")
            except Exception as e: st.error(f"錯誤: {e}")

        st.subheader("📊 盈虧報表"); 
        if st.button("查詢今日盈虧"):
             q_start = datetime.now().strftime("%Y-%m-%d 00:00:00"); q_end = datetime.now().strftime("%Y-%m-%d 23:59:59")
             df = pd.read_sql_query("SELECT * FROM Game_Transactions WHERE timestamp >= ? AND timestamp <= ?", conn, params=(q_start, q_end))
             st.dataframe(df)

    with tabs[3]: # 系統與維護
        if user_role == "老闆":
             with st.expander("🎨 視覺與公告"):
                new_title = st.text_input("登入主標題", value=m_title)
                new_lb1 = st.text_input("榜單標題 1", value=lb_title_1)
                new_lb2 = st.text_input("榜單標題 2", value=lb_title_2)
                rank_desc = st.text_area("排位卡背面說明", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='rank_card_desc'").fetchone() or ("排位與積分規則請見遊戲大廳說明。",))[0])
                vip_desc = st.text_input("VIP卡正面Slogan", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='vip_card_desc'").fetchone() or ("VIP 點數可用於兌換專屬商品與特權。",))[0])
                
                st.markdown("---")
                st.write("📢 **跑馬燈設定**")
                new_m_txt = st.text_input("跑馬燈內容", value=m_txt)
                new_m_spd = st.slider("捲動速度 (越小越快)", 10, 100, int(m_spd))
                new_m_mode = st.selectbox("模式", ["custom", "auto"], index=0 if m_mode=="custom" else 1)
                
                st.write("📢 **自動廣播觸發門檻**")
                th_xp = st.number_input("XP 大獎門檻", value=int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='marquee_th_xp'").fetchone() or ("5000",))[0]))
                th_val = st.number_input("物品價值門檻", value=int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='marquee_th_val'").fetchone() or ("10000",))[0]))

                if st.button("保存視覺與公告"):
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('welcome_title', ?)", (new_title,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('leaderboard_title_1', ?)", (new_lb1,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('leaderboard_title_2', ?)", (new_lb2,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('rank_card_desc', ?)", (rank_desc,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('vip_card_desc', ?)", (vip_desc,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_text', ?)", (new_m_txt,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_speed', ?)", (str(new_m_spd),))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_mode', ?)", (new_m_mode,))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_th_xp', ?)", (str(th_xp),))
                        tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('marquee_th_val', ?)", (str(th_val),))
                        tx_conn.commit()
                    st.success("已更新"); st.rerun()

             max_r_val = st.number_input("防內鬼：單筆核銷上限", value=int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='max_redeem_val'").fetchone() or ("1000000",))[0]))
             if st.button("設定上限"):
                 with sqlite3.connect('poker_data.db') as tx_conn:
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('max_redeem_val', ?)", (str(max_r_val),)); tx_conn.commit()
                 st.success("設定完成")
        
        with st.expander("🎮 遊戲參數與限額設定"):
             st.write("🕹️ **遊戲營運開關**")
             c1, c2, c3, c4, c5 = st.columns(5)
             s_mines = c1.checkbox("掃雷", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='status_mines'").fetchone() or ("ON",))[0]=="ON")
             s_wheel = c2.checkbox("轉盤", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='status_wheel'").fetchone() or ("ON",))[0]=="ON")
             s_bj = c3.checkbox("21點", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='status_blackjack'").fetchone() or ("ON",))[0]=="ON")
             s_bacc = c4.checkbox("百家樂", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='status_baccarat'").fetchone() or ("ON",))[0]=="ON")
             s_roul = c5.checkbox("輪盤", value=(conn.execute("SELECT config_value FROM System_Settings WHERE config_key='status_roulette'").fetchone() or ("ON",))[0]=="ON")
             
             if st.button("💾 更新營運狀態"):
                 with sqlite3.connect('poker_data.db') as tx_conn:
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('status_mines', ?)", ('ON' if s_mines else 'OFF',))
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('status_wheel', ?)", ('ON' if s_wheel else 'OFF',))
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('status_blackjack', ?)", ('ON' if s_bj else 'OFF',))
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('status_baccarat', ?)", ('ON' if s_bacc else 'OFF',))
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('status_roulette', ?)", ('ON' if s_roul else 'OFF',))
                     tx_conn.commit()
                 st.success("已更新"); time.sleep(0.5); st.rerun()

             st.write("---")
             for g_key, g_name in [('blackjack', '21點'), ('mines', '掃雷'), ('baccarat', '百家樂'), ('roulette', '輪盤')]:
                st.write(f"**{g_name} 設定**")
                c1, c2, c3 = st.columns(3)
                cur_rtp = float((conn.execute("SELECT config_value FROM System_Settings WHERE config_key=?", (f'rtp_{g_key}',)).fetchone() or ("0.95",))[0])
                cur_min = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key=?", (f'min_bet_{g_key}',)).fetchone() or ("100",))[0])
                cur_max = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key=?", (f'max_bet_{g_key}',)).fetchone() or ("10000",))[0])
                
                nr = c1.slider(f"RTP ({g_name})", 0.0, 1.0, cur_rtp, 0.01, key=f"rtp_{g_key}_slider")
                nm = c2.number_input(f"Min Bet", value=cur_min, key=f"min_{g_key}_input")
                nx = c3.number_input(f"Max Bet", value=cur_max, key=f"max_{g_key}_input")
                
                if st.button(f"💾 保存 {g_name}", key=f"save_{g_key}"):
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute(f"INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('rtp_{g_key}', ?)", (str(nr),))
                        tx_conn.execute(f"INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('min_bet_{g_key}', ?)", (str(nm),))
                        tx_conn.execute(f"INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('max_bet_{g_key}', ?)", (str(nx),))
                        tx_conn.commit()
                    st.success("Saved")
             
             st.write("---")
             st.write("**🎡 撲洛幸運大轉盤 (小瑪莉) 設定**")
             w_cost = int((conn.execute("SELECT config_value FROM System_Settings WHERE config_key='min_bet_wheel'").fetchone() or ("100",))[0])
             nw_cost = st.number_input("啟動消耗 XP", value=w_cost)
             if st.button("💾 保存 轉盤設定"):
                 with sqlite3.connect('poker_data.db') as tx_conn:
                     tx_conn.execute("INSERT OR REPLACE INTO System_Settings (config_key, config_value) VALUES ('min_bet_wheel', ?)", (str(nw_cost),))
                     tx_conn.commit()
                 st.success("Saved")

        st.subheader("📜 任務管理")
        ms = pd.read_sql_query("SELECT * FROM Missions", conn)
        for _, m in ms.iterrows():
            with st.expander(f"{m['title']} ({m['status']})"):
                c1, c2, c3, c4, c5 = st.columns(5)
                nt = c1.text_input(f"標題", value=m['title'], key=f"mt_{m['id']}")
                nd = c2.text_input(f"描述", value=m['description'], key=f"md_{m['id']}")
                nr = c3.number_input(f"獎勵 XP", value=m['reward_xp'], key=f"mr_{m['id']}")
                ntv = c4.number_input(f"目標數", value=m['target_value'], key=f"mv_{m['id']}")
                nstat = c5.selectbox("狀態", ["Active", "Paused"], index=0 if m['status']=="Active" else 1, key=f"mst_{m['id']}")
                
                if st.button("保存修改", key=f"msv_{m['id']}"):
                    with sqlite3.connect('poker_data.db') as tx_conn:
                        tx_conn.execute("UPDATE Missions SET title=?, description=?, reward_xp=?, target_value=?, status=? WHERE id=?", (nt, nd, nr, ntv, nstat, m['id'])); tx_conn.commit()
                    st.success("已更新"); st.rerun()
                if st.button("刪除", key=f"del_m_{m['id']}"):
                    with sqlite3.connect('poker_data.db') as tx_conn:
                         tx_conn.execute("DELETE FROM Missions WHERE id=?", (m['id'],)); tx_conn.commit()
                    st.rerun()

        st.subheader("🗑️ 結算與重置")
        sch = st.selectbox("賽季方案", ["A方案: 全體扣除 150 分", "B方案: 全體扣除 10%", "C方案: 指定排位手動扣分", "📉 軟重置 (Soft Reset)"]);
        if st.button("執行方案"):
            with sqlite3.connect('poker_data.db') as tx_conn:
                if "A" in sch: tx_conn.execute("UPDATE Leaderboard SET hero_points = MAX(0, hero_points - 150) WHERE player_id != '330999'")
                elif "B" in sch: tx_conn.execute("UPDATE Leaderboard SET hero_points = CAST(hero_points * 0.9 AS INTEGER) WHERE player_id != '330999'")
                elif "軟重置" in sch: tx_conn.execute("UPDATE Leaderboard SET hero_points = CAST(hero_points * 0.4 AS INTEGER) WHERE player_id != '330999'")
                tx_conn.commit()
            st.success("完成")
            
        if user_role == "老闆":
            st.markdown("### ⚖️ 上帝之手 (手動/批量調整)")
            c1, c2, c3 = st.columns(3)
            adj_pid = c1.text_input("玩家 ID", key="god_hand_player_id") 
            adj_val = c2.number_input("增減積分", value=0)
            if c3.button("調整個人積分"):
                with sqlite3.connect('poker_data.db') as tx_conn:
                     tx_conn.execute("UPDATE Leaderboard SET hero_points = hero_points + ? WHERE player_id = ?", (adj_val, adj_pid)); tx_conn.commit()
                st.success("已調整")
            
        st.subheader("💾 備份與還原")
        if os.path.exists('poker_data.db'):
            with open('poker_data.db', 'rb') as f: st.download_button("📥 下載 DB", f, "Backup.db")
        
        if user_role == "老闆":
            rf = st.file_uploader("上傳還原 DB", type="db")
            if rf and st.button("🚨 執行還原"):
                with open('poker_data.db', 'wb') as f: f.write(rf.getbuffer()); st.success("還原成功"); st.rerun()
            
            st.info("清除 >30天遊戲紀錄 與 >90天日誌")
            if st.button("🚀 系統優化 (Vacuum)"):
                # Fixed Vacuum Logic: Separate Transaction
                with sqlite3.connect('poker_data.db') as tx_conn:
                    tx_conn.execute("DELETE FROM Prizes WHERE source LIKE 'GameWin-%' AND time < date('now', '-30 days')")
                    tx_conn.execute("DELETE FROM Staff_Logs WHERE time < date('now', '-90 days')")
                    tx_conn.commit()
                
                # Separate connection for VACUUM (must be autocommit)
                try:
                    v_conn = sqlite3.connect('poker_data.db', isolation_level=None)
                    v_conn.execute("VACUUM")
                    v_conn.close()
                    st.success("優化完成")
                except Exception as e:
                    st.error(f"優化失敗: {e}")

conn.close()