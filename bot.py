#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import string
import asyncio
import logging
import re
import subprocess
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import cloudscraper
import curl_cffi.requests as curl_requests
from colorama import init, Fore
import ssl
import socket
import socks
import base64
import hashlib
import hmac

init(autoreset=True)

# ============= OTOMATİK PAKET KURULUMU =============
def install_packages():
    packages = [
        "flask",
        "flask-cors",
        "requests",
        "cloudscraper",
        "curl_cffi",
        "brotli",
        "zstandard",
        "pysocks",
        "urllib3",
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
app = Flask(__name__)
CORS(app)

# ============= KONFIGÜRASYON =============
API_VERSION = "2.0.0"
API_NAME = "Super CC Checker API"
API_URL = "https://yartyccfurry.onrender.com"

# ============= SÜPER GÜÇLÜ USER-AGENT'LER =============
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 OPR/149.0.0.0",
]

# ============= GOOGLEBOT USER-AGENT =============
GOOGLEBOT_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +https://www.google.com/bot.html)",
    "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +https://www.google.com/bot.html)",
]

# ============= SÜPER HEADERS =============
SUPER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8,de;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "DNT": "1",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Google Chrome";v="149", "Chromium";v="149", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# ============= PROXY YÖNETİCİ =============
class ProxyManager:
    def __init__(self):
        self.proxies = self.load_proxies()
        self.index = 0
    
    def load_proxies(self):
        proxies = []
        http_proxies = [
            "http://189.240.60.164:9090", "http://190.189.114.74:999",
            "http://177.234.159.14:999", "http://200.7.86.202:999",
            "http://201.221.162.81:999", "http://187.216.52.76:999",
            "http://189.203.194.154:999", "http://170.239.218.40:999",
            "http://186.2.244.100:999", "http://181.143.224.130:999",
            "http://186.238.133.194:999", "http://190.128.192.42:999",
            "http://177.54.169.122:999", "http://187.190.198.172:999",
            "http://200.35.160.226:999", "http://190.14.248.150:999",
            "http://190.15.209.74:999", "http://181.53.15.230:999",
            "http://191.102.148.110:999", "http://177.220.164.2:999",
        ]
        
        socks_proxies = [
            "socks5://190.189.114.74:1080",
            "socks5://177.234.159.14:1080",
            "socks5://200.7.86.202:1080",
        ]
        
        for p in http_proxies:
            proxies.append({"http": p, "https": p})
        
        for p in socks_proxies:
            proxies.append({"http": p, "https": p})
        
        return proxies
    
    def get_proxy(self):
        if self.proxies:
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy
        return None

# ============= SÜPER GÜÇLÜ API CLIENT =============
class SuperAPIClient:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.session = requests.Session()
        self.scraper = cloudscraper.create_scraper()
        self.curl_session = curl_requests.Session()
        self.setup_session()
        self.session_count = 0
    
    def setup_session(self):
        retry_strategy = Retry(
            total=10,
            backoff_factor=3,
            status_forcelist=[429, 500, 502, 503, 504, 403, 401, 404, 408],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=200,
            pool_maxsize=200
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        headers = SUPER_HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS + GOOGLEBOT_AGENTS)
        
        self.session.headers.update(headers)
        self.scraper.headers.update(headers)
        self.curl_session.headers.update(headers)
        
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_random_user_agent(self):
        return random.choice(USER_AGENTS + GOOGLEBOT_AGENTS)
    
    def make_request(self, endpoint, data=None, method="GET", use_googlebot=False):
        url = f"{API_URL}{endpoint}"
        self.session_count += 1
        
        if self.session_count % 10 == 0:
            self.setup_session()
        
        for attempt in range(8):
            try:
                proxy = self.proxy_manager.get_proxy()
                user_agent = random.choice(GOOGLEBOT_AGENTS) if use_googlebot else self.get_random_user_agent()
                
                current_headers = SUPER_HEADERS.copy()
                current_headers["User-Agent"] = user_agent
                
                methods = [
                    ("cloudscraper", self.scraper),
                    ("curl", self.curl_session),
                    ("requests", self.session)
                ]
                
                for method_name, session in methods:
                    try:
                        session.headers.update(current_headers)
                        
                        if method == "GET":
                            response = session.get(url, proxies=proxy, timeout=60)
                        else:
                            response = session.post(url, json=data, proxies=proxy, timeout=60)
                        
                        if response.status_code == 200:
                            return response.json()
                        elif response.status_code == 429:
                            time.sleep(10)
                            continue
                        elif response.status_code in [403, 401, 404]:
                            proxy = self.proxy_manager.get_proxy()
                            continue
                        else:
                            time.sleep(3)
                            continue
                            
                    except Exception as e:
                        logging.warning(f"{method_name} hatası: {e}")
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                logging.error(f"İstek hatası (deneme {attempt+1}): {e}")
                time.sleep(3)
                continue
        
        try:
            response = requests.get(url, timeout=30, headers=SUPER_HEADERS)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None

api_client = SuperAPIClient()

# ============= CC CHECKER SINIFI =============
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
    def check_card(card_data):
        return api_client.make_request("/api/check-single", card_data, "POST", use_googlebot=True)

# ============= HTML TEMPLATE =============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ api_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a, #1a1a2e, #16213e);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 40px 0;
            border-bottom: 2px solid #e94560;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3rem;
            background: linear-gradient(45deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 30px rgba(233, 69, 96, 0.3);
        }
        .header p {
            color: #aaa;
            font-size: 1.1rem;
            margin-top: 10px;
        }
        .badge {
            display: inline-block;
            background: #e94560;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-top: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            border-color: #e94560;
        }
        .stat-card .number {
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(45deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-card .label {
            color: #aaa;
            margin-top: 5px;
        }
        .endpoints {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .endpoint-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s;
        }
        .endpoint-card:hover {
            transform: translateY(-5px);
            border-color: #e94560;
            box-shadow: 0 10px 30px rgba(233, 69, 96, 0.2);
        }
        .endpoint-card .method {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 5px;
            font-size: 0.7rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .method.get { background: #4CAF50; }
        .method.post { background: #FF9800; }
        .method.put { background: #2196F3; }
        .method.delete { background: #f44336; }
        .endpoint-card .path {
            font-size: 1.2rem;
            font-weight: bold;
            color: #fff;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .endpoint-card .desc {
            color: #aaa;
            font-size: 0.9rem;
            margin: 10px 0;
        }
        .endpoint-card .example {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            color: #8f8;
            overflow-x: auto;
            margin-top: 10px;
        }
        .endpoint-card .example .url {
            color: #ff6b6b;
        }
        .endpoint-card .example .json {
            color: #ffd93d;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            margin-top: 40px;
        }
        .footer a {
            color: #e94560;
            text-decoration: none;
        }
        .status-badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 10px;
        }
        .status-badge.online { background: #4CAF50; color: #fff; }
        .status-badge.offline { background: #f44336; color: #fff; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .feature {
            background: rgba(255, 255, 255, 0.03);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .feature .icon { font-size: 2rem; margin-bottom: 5px; }
        .feature .name { color: #aaa; font-size: 0.9rem; }
        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .endpoints { grid-template-columns: 1fr; }
            .stats { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 {{ api_name }}</h1>
            <p>Süper Güçlü CC Checker API - Tüm korumaları aşar!</p>
            <span class="badge">v{{ version }}</span>
            <span class="status-badge {{ status_class }}">{{ status_text }}</span>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number">{{ total_endpoints }}</div>
                <div class="label">📌 Toplam Endpoint</div>
            </div>
            <div class="stat-card">
                <div class="number">{{ proxy_count }}</div>
                <div class="label">🔄 Proxy Sayısı</div>
            </div>
            <div class="stat-card">
                <div class="number">8</div>
                <div class="label">🔄 Deneme Sayısı</div>
            </div>
            <div class="stat-card">
                <div class="number">3</div>
                <div class="label">🔧 İstek Yöntemi</div>
            </div>
        </div>

        <h2 style="margin: 30px 0 20px 0; color: #e94560;">📡 Endpoint'ler</h2>
        <div class="endpoints">
            {% for endpoint in endpoints %}
            <div class="endpoint-card">
                <span class="method {{ endpoint.method.lower() }}">{{ endpoint.method }}</span>
                <div class="path">{{ endpoint.path }}</div>
                <div class="desc">{{ endpoint.description }}</div>
                <div class="example">
                    <div><span class="url">URL:</span> {{ endpoint.example.url }}</div>
                    {% if endpoint.example.body %}
                    <div><span class="json">Body:</span> {{ endpoint.example.body }}</div>
                    {% endif %}
                    <div><span class="json">Curl:</span> {{ endpoint.example.curl }}</div>
                </div>
            </div>
            {% endfor %}
        </div>

        <h2 style="margin: 30px 0 20px 0; color: #e94560;">⚡ Özellikler</h2>
        <div class="features">
            <div class="feature">
                <div class="icon">🛡️</div>
                <div class="name">Cloudflare Bypass</div>
            </div>
            <div class="feature">
                <div class="icon">🤖</div>
                <div class="name">Googlebot Taklidi</div>
            </div>
            <div class="feature">
                <div class="icon">🔄</div>
                <div class="name">20+ Proxy</div>
            </div>
            <div class="feature">
                <div class="icon">🔧</div>
                <div class="name">3 İstek Yöntemi</div>
            </div>
            <div class="feature">
                <div class="icon">⚡</div>
                <div class="name">8 Deneme</div>
            </div>
            <div class="feature">
                <div class="icon">📡</div>
                <div class="name">SOCKS5 Desteği</div>
            </div>
        </div>

        <div class="footer">
            <p>💻 {{ api_name }} | © 2026 | <a href="{{ api_url }}">{{ api_url }}</a></p>
            <p style="color: #444; font-size: 0.8rem; margin-top: 5px;">🔥 Süper güçlü, tüm korumaları aşan CC Checker API</p>
        </div>
    </div>
</body>
</html>
"""

# ============= ANA SAYFA =============
@app.route('/', methods=['GET'])
def home():
    """Ana sayfa - API dokümantasyonu"""
    endpoints = [
        {
            "method": "GET",
            "path": "/",
            "description": "API ana sayfası - dokümantasyon",
            "example": {
                "url": f"{API_URL}/",
                "curl": f"curl {API_URL}/"
            }
        },
        {
            "method": "GET",
            "path": "/api/generate",
            "description": "Rastgele kart üret (count parametresi ile adet belirtebilirsin)",
            "example": {
                "url": f"{API_URL}/api/generate?count=5",
                "curl": f"curl {API_URL}/api/generate?count=5"
            }
        },
        {
            "method": "POST",
            "path": "/api/check-single",
            "description": "Tek kart kontrol et",
            "example": {
                "url": f"{API_URL}/api/check-single",
                "body": '{"number":"4111111111111111","month":"12","year":"2026","cvv":"123"}',
                "curl": f"curl -X POST {API_URL}/api/check-single -H 'Content-Type: application/json' -d '{{\"number\":\"4111111111111111\",\"month\":\"12\",\"year\":\"2026\",\"cvv\":\"123\"}}'"
            }
        },
        {
            "method": "POST",
            "path": "/api/check",
            "description": "Çoklu kart kontrol et",
            "example": {
                "url": f"{API_URL}/api/check",
                "body": '{"cards":[{"number":"4111111111111111","month":"12","year":"2026","cvv":"123"}]}',
                "curl": f"curl -X POST {API_URL}/api/check -H 'Content-Type: application/json' -d '{{\"cards\":[{{\"number\":\"4111111111111111\",\"month\":\"12\",\"year\":\"2026\",\"cvv\":\"123\"}}]}}'"
            }
        },
        {
            "method": "GET",
            "path": "/api/stats",
            "description": "API istatistikleri",
            "example": {
                "url": f"{API_URL}/api/stats",
                "curl": f"curl {API_URL}/api/stats"
            }
        },
        {
            "method": "GET",
            "path": "/api/health",
            "description": "API sağlık kontrolü",
            "example": {
                "url": f"{API_URL}/api/health",
                "curl": f"curl {API_URL}/api/health"
            }
        }
    ]
    
    # API durumu
    try:
        response = requests.get(f"{API_URL}/api/stats", timeout=5)
        status_online = response.status_code == 200
    except:
        status_online = False
    
    return render_template_string(
        HTML_TEMPLATE,
        api_name=API_NAME,
        version=API_VERSION,
        api_url=API_URL,
        total_endpoints=len(endpoints),
        proxy_count=len(api_client.proxy_manager.proxies),
        endpoints=endpoints,
        status_text="🟢 Online" if status_online else "🔴 Offline",
        status_class="online" if status_online else "offline"
    )

# ============= API ENDPOINT'LERİ =============
@app.route('/api/generate', methods=['GET'])
def generate_cards():
    """Rastgele kart üret"""
    try:
        count = request.args.get('count', default=1, type=int)
        count = min(max(count, 1), 100)
        
        cards = []
        for _ in range(count):
            card = CCChecker.generate_card()
            cards.append(card)
        
        return jsonify({
            "status": "success",
            "count": len(cards),
            "cards": cards,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/check-single', methods=['POST'])
def check_single_card():
    """Tek kart kontrol"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        required = ['number', 'month', 'year', 'cvv']
        for field in required:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing field: {field}",
                    "timestamp": datetime.now().isoformat()
                }), 400
        
        # Kartı kontrol et
        result = CCChecker.check_card(data)
        
        if result and result.get('status') == 'success':
            return jsonify({
                "status": "success",
                "result": result.get('result', {}),
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Doğrudan API'ye istek dene
            try:
                direct = requests.post(
                    f"{API_URL}/api/check-single",
                    json=data,
                    timeout=30,
                    headers=SUPER_HEADERS
                )
                if direct.status_code == 200:
                    return jsonify({
                        "status": "success",
                        "result": direct.json().get('result', {}),
                        "timestamp": datetime.now().isoformat()
                    })
            except:
                pass
            
            return jsonify({
                "status": "error",
                "message": "Card check failed - API unreachable",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/check', methods=['POST'])
def check_multiple_cards():
    """Çoklu kart kontrol"""
    try:
        data = request.get_json()
        if not data or 'cards' not in data:
            return jsonify({
                "status": "error",
                "message": "No cards provided",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        cards = data.get('cards', [])
        if not isinstance(cards, list):
            return jsonify({
                "status": "error",
                "message": "Cards must be an array",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        results = []
        live_count = 0
        
        for card in cards:
            result = CCChecker.check_card(card)
            if result and result.get('status') == 'success':
                result_data = result.get('result', {})
                if result_data.get('status') == 'approved':
                    live_count += 1
                results.append(result_data)
            else:
                results.append({
                    "card": card,
                    "status": "error",
                    "message": "Check failed"
                })
        
        return jsonify({
            "status": "success",
            "total": len(results),
            "live_count": live_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """API istatistikleri"""
    return jsonify({
        "status": "success",
        "name": API_NAME,
        "version": API_VERSION,
        "api_url": API_URL,
        "proxy_count": len(api_client.proxy_manager.proxies),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/": "Ana sayfa - dokümantasyon",
            "/api/generate": "Kart üret",
            "/api/check-single": "Tek kart kontrol",
            "/api/check": "Çoklu kart kontrol",
            "/api/stats": "İstatistikler",
            "/api/health": "Sağlık kontrolü"
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Sağlık kontrolü"""
    try:
        # Ana API'ye istek at
        response = requests.get(f"{API_URL}/api/stats", timeout=5)
        main_api_status = response.status_code == 200
    except:
        main_api_status = False
    
    return jsonify({
        "status": "healthy" if main_api_status else "degraded",
        "main_api": "online" if main_api_status else "offline",
        "proxy_count": len(api_client.proxy_manager.proxies),
        "timestamp": datetime.now().isoformat()
    })

# ============= CORS DESTEĞİ =============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ============= HATA YÖNETİMİ =============
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/api/generate",
            "/api/check-single",
            "/api/check",
            "/api/stats",
            "/api/health"
        ],
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }), 500

# ============= BOTU BAŞLAT =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 {API_NAME} başlatılıyor...")
    print(f"📡 API URL: {API_URL}")
    print(f"🔄 Proxy sayısı: {len(api_client.proxy_manager.proxies)}")
    print(f"🔧 Port: {port}")
    print("✅ API çalışıyor!")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
