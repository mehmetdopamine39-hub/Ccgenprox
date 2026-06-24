#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import string
import asyncio
import sqlite3
import logging
import re
import base64
import uuid
import subprocess
import importlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# ============= OTOMATİK PAKET KURULUMU =============
def install_packages():
    packages = [
        "python-telegram-bot",
        "requests",
        "aiohttp",
        "pysocks",
        "urllib3",
        "httpx",
        "certifi",
        "charset-normalizer",
        "idna",
        "cloudscraper",
        "curl_cffi",
        "colorama"
    ]
    
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            print(f"📦 {pkg} kuruluyor...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
    
    print("✅ Tüm paketler kuruldu!")

install_packages()

# ============= ANA KOD =============
import requests
import aiohttp
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import cloudscraper
import curl_cffi.requests as curl_requests
from colorama import init, Fore

init(autoreset=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============= KONFIGÜRASYON =============
BOT_TOKEN = "8827662254:AAEAnhpLxgzgZ1gJWRYFmBtkt_OwYCrkpUc"
ADMIN_IDS = [8610336203, 8928323846]
OWNER_ID = 8610336203
CHANNEL_USERNAME = "@yartyccfurry"
DAILY_LIMIT = 5
PREMIUM_LIMIT = 100
MAX_CLONE_BOTS = 2
DB_NAME = "bot_data.db"
MAIN_API_URL = "https://yartyccfurry.onrender.com"

API_ENDPOINTS = {
    "generate": f"{MAIN_API_URL}/api/generate",
    "check_single": f"{MAIN_API_URL}/api/check-single",
    "check_multiple": f"{MAIN_API_URL}/api/check",
    "stats": f"{MAIN_API_URL}/api/stats"
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============= VERİTABANI =============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expiry TEXT,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                total_checks INTEGER DEFAULT 0,
                daily_checks INTEGER DEFAULT 0,
                refer_count INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                date TEXT,
                checks INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                card_number TEXT,
                card_month TEXT,
                card_year TEXT,
                card_cvv TEXT,
                status TEXT,
                gateway TEXT,
                message TEXT,
                check_date TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clone_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT UNIQUE,
                bot_username TEXT,
                owner_id INTEGER,
                clone_date TEXT,
                is_active INTEGER DEFAULT 1,
                total_checks INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy TEXT,
                type TEXT,
                is_active INTEGER DEFAULT 1,
                last_used TEXT,
                fail_count INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, join_date, total_checks, daily_checks)
            VALUES (?, ?, ?, ?, ?, 0, 0)
        ''', (user_id, username or "", first_name or "", last_name or "", datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_user(self, user_id, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
        self.conn.commit()
    
    def get_daily_checks(self, user_id):
        today = datetime.now().date().isoformat()
        self.cursor.execute('SELECT checks FROM daily_usage WHERE user_id = ? AND date = ?', (user_id, today))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def add_daily_check(self, user_id):
        today = datetime.now().date().isoformat()
        self.cursor.execute('''
            INSERT INTO daily_usage (user_id, date, checks) 
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET checks = checks + 1
        ''', (user_id, today))
        self.conn.commit()
    
    def get_remaining_checks(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        if user[7] == 1:
            return 999999
        if user[5] == 1:
            expiry = user[6]
            if expiry and datetime.now().isoformat() < expiry:
                return PREMIUM_LIMIT - self.get_daily_checks(user_id)
        return DAILY_LIMIT - self.get_daily_checks(user_id)
    
    def add_card_result(self, user_id, card, status, gateway, message):
        self.cursor.execute('''
            INSERT INTO card_results 
            (user_id, card_number, card_month, card_year, card_cvv, status, gateway, message, check_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, card.get('number', ''), card.get('month', ''), card.get('year', ''), 
              card.get('cvv', ''), status, gateway, message[:500], datetime.now().isoformat()))
        self.conn.commit()
        self.cursor.execute('UPDATE users SET total_checks = total_checks + 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as live,
                   SUM(CASE WHEN status = 'declined' THEN 1 ELSE 0 END) as dead
            FROM card_results WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, username, first_name, last_name, is_premium, is_banned FROM users')
        return self.cursor.fetchall()
    
    def add_clone_bot(self, bot_token, bot_username, owner_id):
        self.cursor.execute('SELECT COUNT(*) FROM clone_bots WHERE owner_id = ? AND is_active = 1', (owner_id,))
        count = self.cursor.fetchone()[0]
        if count >= MAX_CLONE_BOTS:
            return False, f"Maximum {MAX_CLONE_BOTS} clone bot allowed!"
        
        self.cursor.execute('''
            INSERT INTO clone_bots (bot_token, bot_username, owner_id, clone_date)
            VALUES (?, ?, ?, ?)
        ''', (bot_token, bot_username, owner_id, datetime.now().isoformat()))
        self.conn.commit()
        return True, "Clone bot added successfully!"
    
    def get_clone_bots(self, owner_id):
        self.cursor.execute('SELECT id, bot_token, bot_username, clone_date, is_active, total_checks FROM clone_bots WHERE owner_id = ?', (owner_id,))
        return self.cursor.fetchall()
    
    def remove_clone_bot(self, bot_id, owner_id):
        self.cursor.execute('UPDATE clone_bots SET is_active = 0 WHERE id = ? AND owner_id = ?', (bot_id, owner_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_clone_bots(self):
        self.cursor.execute('SELECT id, bot_token, bot_username, owner_id, clone_date, is_active, total_checks FROM clone_bots WHERE is_active = 1')
        return self.cursor.fetchall()

# ============= API CLIENT =============
class APIClient:
    def __init__(self):
        self.session = requests.Session()
        self.scraper = cloudscraper.create_scraper()
        self.curl_session = curl_requests.Session()
        self.setup_session()
        self.proxies = self.load_proxies()
        self.proxy_index = 0
    
    def load_proxies(self):
        proxies = []
        proxy_list = [
            "http://189.240.60.164:9090", "http://190.189.114.74:999",
            "http://177.234.159.14:999", "http://200.7.86.202:999",
            "http://201.221.162.81:999", "http://187.216.52.76:999",
            "http://189.203.194.154:999", "http://170.239.218.40:999",
            "http://186.2.244.100:999", "http://181.143.224.130:999",
        ]
        for p in proxy_list:
            proxies.append({"http": p, "https": p})
        return proxies
    
    def setup_session(self):
        retry_strategy = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504, 403, 401])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "DNT": "1",
            "Pragma": "no-cache"
        }
        self.session.headers.update(headers)
        self.scraper.headers.update(headers)
        self.curl_session.headers.update(headers)
    
    def get_proxy(self):
        if self.proxies:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            self.proxy_index += 1
            return proxy
        return None
    
    def make_request(self, endpoint, data=None, method="GET"):
        url = f"{MAIN_API_URL}{endpoint}"
        
        for attempt in range(5):
            try:
                proxy = self.get_proxy()
                
                try:
                    if method == "GET":
                        response = self.scraper.get(url, proxies=proxy, timeout=30)
                    else:
                        response = self.scraper.post(url, json=data, proxies=proxy, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                except:
                    pass
                
                try:
                    if method == "GET":
                        response = self.curl_session.get(url, proxies=proxy, timeout=30, impersonate="chrome120")
                    else:
                        response = self.curl_session.post(url, json=data, proxies=proxy, timeout=30, impersonate="chrome120")
                    if response.status_code == 200:
                        return response.json()
                except:
                    pass
                
                if method == "GET":
                    response = self.session.get(url, proxies=proxy, timeout=30)
                else:
                    response = self.session.post(url, json=data, proxies=proxy, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    time.sleep(5)
                    continue
                else:
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                logger.error(f"İstek hatası: {e}")
                time.sleep(2)
                continue
        
        return None
    
    def test_api(self):
        try:
            response = self.session.get(f"{MAIN_API_URL}/api/stats", timeout=10)
            return response.status_code == 200
        except:
            return False

# ============= CC CHECKER =============
class CCChecker:
    @staticmethod
    def generate_card():
        bins = [
            "4" + ''.join(random.choices(string.digits, k=5)),
            "5" + ''.join(random.choices(string.digits, k=5)),
            "3" + ''.join(random.choices(string.digits, k=5)),
            "6" + ''.join(random.choices(string.digits, k=5)),
        ]
        bin_num = random.choice(bins)
        remaining = 15 - len(bin_num) if bin_num.startswith('3') else 16 - len(bin_num)
        card_number = bin_num + ''.join(random.choices(string.digits, k=remaining))
        
        def luhn_checksum(card_number):
            digits = [int(d) for d in str(card_number)]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum([int(x) for x in str(d * 2)])
            return checksum % 10
        
        check_digit = luhn_checksum(card_number[:-1])
        if check_digit != 0:
            check_digit = 10 - check_digit
        card_number = card_number[:-1] + str(check_digit)
        
        return {
            "number": card_number,
            "month": str(random.randint(1, 12)).zfill(2),
            "year": str(random.randint(2026, 2030)),
            "cvv": ''.join(random.choices(string.digits, k=3 if not card_number.startswith('3') else 4))
        }
    
    @staticmethod
    def check_card_via_api(card_data):
        api = APIClient()
        return api.make_request("/api/check-single", card_data, "POST")

# ============= ANA BOT =============
class SuperCardBot:
    def __init__(self):
        self.db = Database()
        self.api = APIClient()
        self.app = None
    
    async def is_admin(self, user_id):
        user = self.db.get_user(user_id)
        return user and (user[7] == 1 or user_id in ADMIN_IDS)
    
    async def is_banned(self, user_id):
        user = self.db.get_user(user_id)
        return user and user[8] == 1
    
    async def check_channel_member(self, user_id):
        try:
            member = await self.app.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except:
            return False
    
    # ============= KOMUTLAR =============
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        self.db.add_user(user_id, user.username, user.first_name, user.last_name)
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if not await self.check_channel_member(user_id):
            keyboard = [[InlineKeyboardButton("📢 Kanala Katil", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
            await update.message.reply_text(f"⚠️ Once kanala katilmalisin!\n🔗 Kanal: {CHANNEL_USERNAME}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        remaining = self.db.get_remaining_checks(user_id)
        user_data = self.db.get_user(user_id)
        is_premium = user_data[5] == 1 if user_data else False
        api_status = "✅" if self.api.test_api() else "❌"
        
        clone_bots = self.db.get_clone_bots(user_id)
        clone_count = len([b for b in clone_bots if b[4] == 1])
        
        welcome_text = f"""
🚀 SUPER CC CHECKER BOT

Merhaba {user.first_name}!

📊 Istatistikler:
• Kalan Hak: {remaining}
• Premium: {'✅ Evet' if is_premium else '❌ Hayir'}
• Toplam Kontrol: {user_data[10] if user_data else 0}
• API Durumu: {api_status}
• Clone Bot: {clone_count}/{MAX_CLONE_BOTS}

📌 Komutlar:
/generate - Rastgele kart uret
/check - Tek kart kontrol
/check_multiple - Coklu kart kontrol
/stats - Istatistikler
/help - Yardim
/premium - Premium bilgileri
/refer - Referans sistemi
/clone - Bot klonla
/myclones - Klon botlarim
/api - API bilgileri

⚡ Ozellikler:
✅ 10+ Proxy destegi
✅ Cloudflare koruma asma
✅ Otomatik API yedekleme
✅ Gunluk 5 ucretsiz hak
✅ Clone bot sistemi
        """
        
        keyboard = [
            [InlineKeyboardButton("🎲 Kart Uret", callback_data="generate"), InlineKeyboardButton("✅ Tek Kart", callback_data="check_single")],
            [InlineKeyboardButton("📋 Coklu Kart", callback_data="check_multiple"), InlineKeyboardButton("📊 Istatistik", callback_data="stats")],
            [InlineKeyboardButton("⭐ Premium", callback_data="premium"), InlineKeyboardButton("👥 Referans", callback_data="refer")],
            [InlineKeyboardButton("🔄 Clone Bot", callback_data="clone"), InlineKeyboardButton("📡 API", callback_data="api")],
            [InlineKeyboardButton("❓ Yardim", callback_data="help"), InlineKeyboardButton("🔄 Guncelle", callback_data="refresh")]
        ]
        
        if await self.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
        
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def generate_cards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if not await self.check_channel_member(user_id):
            await update.message.reply_text(f"⚠️ Once {CHANNEL_USERNAME} kanalina katil!")
            return
        
        remaining = self.db.get_remaining_checks(user_id)
        if remaining <= 0:
            await update.message.reply_text("❌ Gunluk hakkin bitti! Yarin tekrar dene.")
            return
        
        try:
            count = 1
            if context.args and context.args[0].isdigit():
                count = min(int(context.args[0]), remaining, 20)
            
            status_msg = await update.message.reply_text("⏳ Kart uretiliyor...")
            
            cards = []
            for _ in range(count):
                card = CCChecker.generate_card()
                cards.append(card)
            
            if cards:
                self.db.add_daily_check(user_id)
                message = f"🎲 {len(cards)} Kart Uretildi:\n\n"
                for i, card in enumerate(cards, 1):
                    message += f"{i}. {card['number']}|{card['month']}|{card['year']}|{card['cvv']}\n"
                
                remaining = self.db.get_remaining_checks(user_id)
                message += f"\n📊 Kalan Hak: {remaining}"
                
                await status_msg.edit_text(message)
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def check_single_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if not await self.check_channel_member(user_id):
            await update.message.reply_text(f"⚠️ Once {CHANNEL_USERNAME} kanalina katil!")
            return
        
        remaining = self.db.get_remaining_checks(user_id)
        if remaining <= 0:
            await update.message.reply_text("❌ Gunluk hakkin bitti! Yarin tekrar dene.")
            return
        
        try:
            if context.args:
                card_data = context.args[0]
            else:
                await update.message.reply_text("❌ Kart bilgilerini girin!\nFormat: /check 4111111111111111|12|2026|123")
                return
            
            parts = card_data.split('|')
            if len(parts) != 4:
                await update.message.reply_text("❌ Hatali format! Dogru: 4111111111111111|12|2026|123")
                return
            
            card = {
                "number": parts[0].strip(),
                "month": parts[1].strip().zfill(2),
                "year": parts[2].strip(),
                "cvv": parts[3].strip()
            }
            
            status_msg = await update.message.reply_text("⏳ Kart kontrol ediliyor...")
            
            result = await asyncio.to_thread(CCChecker.check_card_via_api, card)
            
            if result and result.get('status') == 'success':
                result_data = result.get('result', {})
                card_status = result_data.get('status', 'unknown')
                gateway = result_data.get('gateway', 'Bilinmiyor')
                message_text = result_data.get('message', '')
                
                self.db.add_card_result(user_id, card, card_status, gateway, message_text)
                self.db.add_daily_check(user_id)
                
                if card_status == 'approved':
                    status_text = "✅ CANLI"
                    await update.message.reply_text("🎉 TEBRIKLER! KART CANLI!")
                elif card_status == 'declined':
                    status_text = "❌ OLU"
                else:
                    status_text = "⚠️ BILINMIYOR"
                
                response_text = f"""
{status_text} Kart Kontrol Sonucu

📱 Kart: {card['number']}
📅 Tarih: {card['month']}/{card['year']}
🔐 CVV: {card['cvv']}
🏦 Gateway: {gateway}
💬 Mesaj: {message_text[:200]}

📊 Kalan Hak: {self.db.get_remaining_checks(user_id)}
                """
                await status_msg.edit_text(response_text)
            else:
                await status_msg.edit_text("❌ Hata olustu! API'ye baglanilamiyor.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")
    
    async def check_multiple_cards(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if not await self.check_channel_member(user_id):
            await update.message.reply_text(f"⚠️ Once {CHANNEL_USERNAME} kanalina katil!")
            return
        
        remaining = self.db.get_remaining_checks(user_id)
        if remaining <= 0:
            await update.message.reply_text("❌ Gunluk hakkin bitti! Yarin tekrar dene.")
            return
        
        await update.message.reply_text(
            "📋 Kartlari gonderin!\n\n"
            "Her karti alt alta yazin:\n"
            "4111111111111111|12|2026|123\n\n"
            "Iptal: /cancel"
        )
        context.user_data['multi_check'] = True
    
    async def clone_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if not await self.check_channel_member(user_id):
            await update.message.reply_text(f"⚠️ Once {CHANNEL_USERNAME} kanalina katil!")
            return
        
        user = self.db.get_user(user_id)
        is_premium = user[5] == 1 if user else False
        
        if not is_premium and user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Clone bot sadece PREMIUM kullanicilara ozeldir!")
            return
        
        clone_bots = self.db.get_clone_bots(user_id)
        active_clones = [b for b in clone_bots if b[4] == 1]
        
        if len(active_clones) >= MAX_CLONE_BOTS:
            await update.message.reply_text(f"❌ Maximum {MAX_CLONE_BOTS} clone bot olusturabilirsin!")
            return
        
        await update.message.reply_text(
            "🤖 Clone Bot Olustur\n\n"
            "BotFather'dan aldigin TOKEN'i gonder:\n"
            "YOUR_BOT_TOKEN\n\n"
            "Iptal: /cancel"
        )
        context.user_data['waiting_clone_token'] = True
    
    async def handle_clone_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = update.message.text.strip()
        
        if token.startswith('/'):
            return
        
        if ':' not in token:
            await update.message.reply_text("❌ Gecersiz token! BotFather'dan aldigin token'i gonder.")
            return
        
        try:
            bot_info = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if bot_info.status_code != 200:
                await update.message.reply_text("❌ Gecersiz token! Bot calismiyor.")
                return
            
            bot_data = bot_info.json()
            if not bot_data.get('ok'):
                await update.message.reply_text("❌ Gecersiz token!")
                return
            
            bot_username = bot_data['result'].get('username', 'Unknown')
            
            success, msg = self.db.add_clone_bot(token, bot_username, user_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Clone Bot Olusturuldu!\n\n"
                    f"🤖 Bot: @{bot_username}\n"
                    f"👤 Sahip: {user_id}\n"
                    f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                await update.message.reply_text(f"❌ {msg}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")
        
        context.user_data['waiting_clone_token'] = False
    
    async def my_clones(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        clone_bots = self.db.get_clone_bots(user_id)
        if not clone_bots:
            await update.message.reply_text("❌ Henuz clone botun yok!\n/clone ile olustur.")
            return
        
        message = "🤖 Klon Botlarin:\n\n"
        for bot in clone_bots:
            status = "✅ Aktif" if bot[4] == 1 else "❌ Pasif"
            message += f"• @{bot[2]} - {status}\n"
            message += f"  Token: {bot[1][:15]}...\n"
            message += f"  Kontrol: {bot[5]}\n"
            message += f"  ID: {bot[0]}\n\n"
        
        keyboard = [[InlineKeyboardButton("🗑️ Klon Bot Sil", callback_data="remove_clone")]]
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def remove_clone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        clone_bots = self.db.get_clone_bots(user_id)
        if not clone_bots:
            await update.message.reply_text("❌ Silinecek clone bot yok!")
            return
        
        keyboard = []
        for bot in clone_bots:
            if bot[4] == 1:
                keyboard.append([InlineKeyboardButton(f"🗑️ @{bot[2]}", callback_data=f"delclone_{bot[0]}")])
        keyboard.append([InlineKeyboardButton("❌ Iptal", callback_data="cancel")])
        
        await update.message.reply_text(
            "🗑️ Silmek istedigin botu sec:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def api_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        api_status = "✅ Calisiyor" if self.api.test_api() else "❌ Calismiyor"
        
        message = f"""
📡 API BILGILERI

🔗 Ana API: {MAIN_API_URL}
📊 Durum: {api_status}
🔄 Proxy Sayisi: {len(self.api.proxies)}

📌 Endpoint'ler:
• /api/generate - Kart uret
• /api/check-single - Tek kart kontrol
• /api/check - Coklu kart kontrol
• /api/stats - Istatistikler

📝 Kullanim:
POST {API_ENDPOINTS['check_single']}
{{
  "number": "4111111111111111",
  "month": "12",
  "year": "2026",
  "cvv": "123"
}}

🔧 Ozellikler:
• 10+ Proxy
• Cloudflare koruma asma
• Otomatik yedekleme
• Hizli kontrol
        """
        
        await update.message.reply_text(message)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        user = self.db.get_user(user_id)
        stats = self.db.get_user_stats(user_id)
        remaining = self.db.get_remaining_checks(user_id)
        
        if not user:
            await update.message.reply_text("❌ Kullanici bulunamadi!")
            return
        
        is_premium = user[5] == 1
        
        message = f"""
📊 ISTATISTIKLERIN

👤 Kullanici: @{user[1] or user[2] or 'Bilinmiyor'}

📊 Kart Istatistikleri:
• Toplam Kontrol: {stats[0] if stats else 0}
• Canli Kart: {stats[1] if stats else 0}
• Olu Kart: {stats[2] if stats else 0}
• Basari Orani: {f"{(stats[1]/stats[0]*100):.1f}%" if stats and stats[0] > 0 else "0%"}

📅 Gunluk Durum:
• Kalan Hak: {remaining}
• Gunluk Limit: {'Sinirsiz' if is_premium else DAILY_LIMIT}

⭐ Premium: {'✅ Aktif' if is_premium else '❌ Pasif'}
        """
        
        await update.message.reply_text(message)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 KULLANIM KILAVUZU

🔹 Temel Komutlar:
/generate - Rastgele kart uret
/check - Tek kart kontrol et
/check_multiple - Coklu kart kontrol et
/stats - Istatistiklerini gor
/help - Bu yardim menusu

🔹 Premium Komutlar:
/premium - Premium paketleri gor
/refer - Referans sistemini kullan
/clone - Bot klonla
/myclones - Klon botlarim

🔹 Admin Komutlari:
/admin - Admin paneli
/broadcast - Duyuru gonder
/add_premium - Premium ver
/remove_premium - Premium al
/ban - Kullanici banla
/unban - Ban kaldir

📋 Kart Formati:
4111111111111111|12|2026|123

⚡ Ozellikler:
• Gunluk 5 ucretsiz hak
• Premium ile sinirsiz
• 10+ Proxy destegi
• Cloudflare koruma asma
• Clone bot sistemi
• Detayli istatistikler
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Istatistikler", callback_data="stats"), InlineKeyboardButton("⭐ Premium", callback_data="premium")],
            [InlineKeyboardButton("🤖 Clone Bot", callback_data="clone"), InlineKeyboardButton("📡 API", callback_data="api")]
        ]
        
        await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = """
⭐ PREMIUM PAKETLER

🚀 Premium ile sinirsiz kontrol!

📦 Paketler:
• 7 Gun - 5$
• 30 Gun - 15$
• 90 Gun - 35$
• 365 Gun - 100$

✨ Premium Avantajlari:
✅ Sinirsiz kart kontrol
✅ Clone bot hakki (2 bot)
✅ Oncelikli destek
✅ Hizli kontrol
✅ Daha yuksek basari orani

📞 Iletisim: @rinexdestek
        """
        await update.message.reply_text(message)
    
    async def refer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            return
        
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        ref_count = user[12] if len(user) > 12 else 0
        
        message = f"""
👥 REFERANS SISTEMI

Her referans icin 1 ekstra hak kazan!

📌 Referans Linkin:
{ref_link}

👤 Toplam Referans: {ref_count}
⭐ Kazanilan Hak: {ref_count}

🎁 Bonus:
10 referans = 7 gun premium
25 referans = 30 gun premium
        """
        
        keyboard = [[InlineKeyboardButton("📤 Paylas", switch_inline_query=ref_link)]]
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ============= ADMIN KOMUTLARI =============
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            await update.message.reply_text("❌ Bu komut sadece adminler icindir!")
            return
        
        users = self.db.get_all_users()
        total_users = len(users)
        premium_users = sum(1 for u in users if u[4] == 1)
        banned_users = sum(1 for u in users if u[5] == 1)
        
        self.db.cursor.execute('SELECT COUNT(*), SUM(CASE WHEN status="approved" THEN 1 ELSE 0 END) FROM card_results')
        total_checks, live_checks = self.db.cursor.fetchone()
        
        clone_bots = self.db.get_all_clone_bots()
        
        message = f"""
👑 ADMIN PANELI

📊 Genel Istatistikler:
• Toplam Kullanici: {total_users}
• Premium Kullanici: {premium_users}
• Yasakli Kullanici: {banned_users}
• Toplam Kontrol: {total_checks or 0}
• Canli Kart: {live_checks or 0}
• Clone Bot: {len(clone_bots)}

📌 Admin Komutlari:
/broadcast - Duyuru gonder
/add_premium - Premium ver
/remove_premium - Premium al
/ban - Kullanici banla
/unban - Ban kaldir
        """
        
        await update.message.reply_text(message)
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Mesaj gir!\nFormat: /broadcast Merhaba herkese!")
            return
        
        message = ' '.join(context.args)
        users = self.db.get_all_users()
        sent = 0
        failed = 0
        
        status_msg = await update.message.reply_text(f"⏳ {len(users)} kullaniciya mesaj gonderiliyor...")
        
        for user in users:
            try:
                await self.app.bot.send_message(user[0], f"📢 DUYURU\n\n{message}")
                sent += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1
        
        await status_msg.edit_text(f"✅ Duyuru gonderildi!\n\n📤 Gonderilen: {sent}\n❌ Basarisiz: {failed}")
    
    async def add_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Kullanici ID ve sure girin!\nFormat: /add_premium 123456 30")
            return
        
        try:
            target_id = int(context.args[0])
            days = int(context.args[1])
            
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            self.db.update_user(target_id, is_premium=1, premium_expiry=expiry)
            
            try:
                await self.app.bot.send_message(target_id, f"⭐ PREMIUM VERILDI!\n\n📅 Sure: {days} gun\n📆 Bitis: {expiry[:10]}")
            except:
                pass
            
            await update.message.reply_text(f"✅ Premium verildi! Kullanici: {target_id}")
        except:
            await update.message.reply_text("❌ Hatali format!")
    
    async def remove_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Kullanici ID girin!\nFormat: /remove_premium 123456")
            return
        
        try:
            target_id = int(context.args[0])
            self.db.update_user(target_id, is_premium=0, premium_expiry=None)
            
            try:
                await self.app.bot.send_message(target_id, "❌ PREMIUM ALINDI!")
            except:
                pass
            
            await update.message.reply_text(f"✅ Premium alindi: {target_id}")
        except:
            await update.message.reply_text("❌ Hatali format!")
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Kullanici ID girin!\nFormat: /ban 123456")
            return
        
        try:
            target_id = int(context.args[0])
            self.db.update_user(target_id, is_banned=1)
            
            try:
                await self.app.bot.send_message(target_id, "🚫 YASAKLANDIN!")
            except:
                pass
            
            await update.message.reply_text(f"✅ Kullanici yasaklandi: {target_id}")
        except:
            await update.message.reply_text("❌ Hatali format!")
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Kullanici ID girin!\nFormat: /unban 123456")
            return
        
        try:
            target_id = int(context.args[0])
            self.db.update_user(target_id, is_banned=0)
            
            try:
                await self.app.bot.send_message(target_id, "✅ YASAK KALDIRILDI!")
            except:
                pass
            
            await update.message.reply_text(f"✅ Yasa kaldirildi: {target_id}")
        except:
            await update.message.reply_text("❌ Hatali format!")
    
    # ============= HANDLER'LAR =============
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        
        data = query.data
        
        if await self.is_banned(user_id):
            await query.edit_message_text("🚫 YASAKLANDIN!")
            return
        
        if data == "generate":
            await self.generate_cards(update, context)
        elif data == "check_single":
            await query.edit_message_text("✅ Format: /check 4111111111111111|12|2026|123")
        elif data == "check_multiple":
            await query.edit_message_text("📋 /check_multiple yazip kartlari gonder.")
        elif data == "stats":
            await self.stats(update, context)
        elif data == "premium":
            await self.premium(update, context)
        elif data == "refer":
            await self.refer(update, context)
        elif data == "help":
            await self.help(update, context)
        elif data == "refresh":
            await query.edit_message_text("🔄 Guncelleniyor...")
            await self.start(update, context)
        elif data == "admin_panel":
            await self.admin_panel(update, context)
        elif data == "clone":
            await self.clone_bot(update, context)
        elif data == "api":
            await self.api_info(update, context)
        elif data == "remove_clone":
            await self.remove_clone(update, context)
        elif data.startswith("delclone_"):
            bot_id = int(data.split("_")[1])
            if self.db.remove_clone_bot(bot_id, user_id):
                await query.edit_message_text("✅ Clone bot silindi!")
            else:
                await query.edit_message_text("❌ Silme basarisiz!")
        elif data == "cancel":
            await query.edit_message_text("✅ Islem iptal edildi!")
    
    async def handle_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        
        if await self.is_banned(user_id):
            await update.message.reply_text("🚫 YASAKLANDIN!")
            return
        
        if context.user_data.get('waiting_clone_token'):
            await self.handle_clone_token(update, context)
            return
        
        if context.user_data.get('multi_check'):
            if text.lower() == '/cancel':
                context.user_data['multi_check'] = False
                await update.message.reply_text("✅ Islem iptal edildi!")
                return
            
            cards = []
            lines = text.strip().split('\n')
            remaining = self.db.get_remaining_checks(user_id)
            max_cards = min(len(lines), remaining)
            
            for line in lines[:max_cards]:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) == 4:
                    cards.append({"number": parts[0].strip(), "month": parts[1].strip().zfill(2), 
                                 "year": parts[2].strip(), "cvv": parts[3].strip()})
            
            if not cards:
                await update.message.reply_text("❌ Gecerli kart bulunamadi!")
                return
            
            status_msg = await update.message.reply_text(f"⏳ {len(cards)} kart kontrol ediliyor...")
            
            results = []
            for card in cards:
                result = await asyncio.to_thread(CCChecker.check_card_via_api, card)
                if result and result.get('status') == 'success':
                    result_data = result.get('result', {})
                    status = result_data.get('status', 'unknown')
                    gateway = result_data.get('gateway', '')
                    message_text = result_data.get('message', '')
                    self.db.add_card_result(user_id, card, status, gateway, message_text)
                    results.append({"card": card, "status": status, "gateway": gateway})
                    self.db.add_daily_check(user_id)
            
            if results:
                live = sum(1 for r in results if r['status'] == 'approved')
                message = f"📊 {len(results)} Kart Kontrol Sonucu:\n✅ Canli: {live}\n❌ Olu: {len(results)-live}\n\n"
                
                for r in results:
                    c = r['card']
                    emoji = "✅" if r['status'] == 'approved' else "❌"
                    message += f"{emoji} {c['number']}|{c['month']}|{c['year']}|{c['cvv']}\n"
                
                message += f"\n📊 Kalan Hak: {self.db.get_remaining_checks(user_id)}"
                await status_msg.edit_text(message)
            else:
                await status_msg.edit_text("❌ Hata olustu!")
            
            context.user_data['multi_check'] = False
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in context.user_data:
            context.user_data.clear()
            await update.message.reply_text("✅ Islem iptal edildi!")
        else:
            await update.message.reply_text("❌ Aktif islem bulunamadi!")
    
    # ============= BOTU BAŞLAT =============
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            temp_app = Application.builder().token(BOT_TOKEN).build()
            loop.run_until_complete(temp_app.bot.delete_webhook())
            
            self.app = Application.builder().token(BOT_TOKEN).build()
            
            self.app.add_handler(CommandHandler("start", self.start))
            self.app.add_handler(CommandHandler("help", self.help))
            self.app.add_handler(CommandHandler("generate", self.generate_cards))
            self.app.add_handler(CommandHandler("check", self.check_single_card))
            self.app.add_handler(CommandHandler("check_multiple", self.check_multiple_cards))
            self.app.add_handler(CommandHandler("stats", self.stats))
            self.app.add_handler(CommandHandler("premium", self.premium))
            self.app.add_handler(CommandHandler("refer", self.refer))
            self.app.add_handler(CommandHandler("clone", self.clone_bot))
            self.app.add_handler(CommandHandler("myclones", self.my_clones))
            self.app.add_handler(CommandHandler("api", self.api_info))
            self.app.add_handler(CommandHandler("cancel", self.cancel))
            
            self.app.add_handler(CommandHandler("admin", self.admin_panel))
            self.app.add_handler(CommandHandler("broadcast", self.broadcast))
            self.app.add_handler(CommandHandler("add_premium", self.add_premium))
            self.app.add_handler(CommandHandler("remove_premium", self.remove_premium))
            self.app.add_handler(CommandHandler("ban", self.ban_user))
            self.app.add_handler(CommandHandler("unban", self.unban_user))
            
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_messages))
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            
            print("🚀 Super CC Checker Bot baslatiliyor...")
            print(f"👑 Adminler: {ADMIN_IDS}")
            print(f"📌 Kanal: {CHANNEL_USERNAME}")
            print(f"📊 Gunluk Limit: {DAILY_LIMIT}")
            print(f"🔄 Proxy sayisi: {len(self.api.proxies)}")
            print(f"📡 API Durumu: {'✅ Calisiyor' if self.api.test_api() else '❌ Calismiyor'}")
            print("✅ Bot calisiyor!")
            
            loop.run_until_complete(self.app.initialize())
            loop.run_until_complete(self.app.start())
            loop.run_until_complete(self.app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0
            ))
            
            loop.run_forever()
            
        except KeyboardInterrupt:
            print("🛑 Bot durduruluyor...")
        except Exception as e:
            print(f"❌ Bot baslatma hatasi: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    bot = SuperCardBot()
    bot.run()
