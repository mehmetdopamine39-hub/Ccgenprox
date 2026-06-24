#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import string
import logging
import subprocess
import hashlib
import base64
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import cloudscraper
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# ============= OTOMATİK PAKET KURULUMU =============
def install_packages():
    packages = [
        "flask",
        "flask-cors",
        "requests",
        "cloudscraper",
        "urllib3",
        "pysocks",
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
API_NAME = "Super CC Checker API"
API_VERSION = "3.0.0"
API_URL = "https://yartyccfurry.onrender.com"
MAX_CARDS = 100

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= USER-AGENT'LER =============
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +https://www.google.com/bot.html)",
]

# ============= HEADERS =============
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "DNT": "1",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

# ============= PROXY YÖNETİCİ =============
class ProxyManager:
    def __init__(self):
        self.proxies = self.load_proxies()
        self.index = 0
    
    def load_proxies(self):
        proxies = []
        proxy_list = [
            "189.240.60.164:9090", "190.189.114.74:999", "177.234.159.14:999",
            "200.7.86.202:999", "201.221.162.81:999", "187.216.52.76:999",
            "189.203.194.154:999", "170.239.218.40:999", "186.2.244.100:999",
            "181.143.224.130:999", "186.238.133.194:999", "190.128.192.42:999",
            "177.54.169.122:999", "187.190.198.172:999", "200.35.160.226:999",
            "190.14.248.150:999", "190.15.209.74:999", "181.53.15.230:999",
            "191.102.148.110:999", "177.220.164.2:999",
        ]
        for p in proxy_list:
            proxies.append({"http": f"http://{p}", "https": f"http://{p}"})
        return proxies
    
    def get_proxy(self):
        if self.proxies:
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy
        return None

# ============= SÜPER API CLIENT =============
class SuperAPIClient:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.session = requests.Session()
        self.scraper = cloudscraper.create_scraper()
        self.setup_clients()
    
    def setup_clients(self):
        retry = Retry(total=10, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504, 403, 401])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_headers(self):
        headers = HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers
    
    def make_request(self, endpoint, data=None, method="GET"):
        url = f"{API_URL}{endpoint}"
        
        for attempt in range(8):
            try:
                proxy = self.proxy_manager.get_proxy()
                headers = self.get_headers()
                
                methods = [
                    ("cloudscraper", self.scraper),
                    ("requests", self.session)
                ]
                
                for method_name, session in methods:
                    try:
                        session.headers.update(headers)
                        
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
                        logger.warning(f"{method_name} hatası: {e}")
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"İstek hatası (deneme {attempt+1}): {e}")
                time.sleep(3)
                continue
        
        return None

api_client = SuperAPIClient()

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
        
        def luhn(card):
            digits = [int(d) for d in str(card)]
            odd = digits[-1::-2]
            even = digits[-2::-2]
            total = sum(odd)
            for d in even:
                total += sum([int(x) for x in str(d * 2)])
            return total % 10
        
        check = luhn(card_number[:-1])
        card_number = card_number[:-1] + str(0 if check == 0 else 10 - check)
        
        return {
            "number": card_number,
            "month": str(random.randint(1, 12)).zfill(2),
            "year": str(random.randint(2026, 2030)),
            "cvv": ''.join(random.choices(string.digits, k=3 if not card_number.startswith('3') else 4))
        }
    
    @staticmethod
    def check_card(card_data):
        return api_client.make_request("/api/check-single", card_data, "POST")

# ============= HTML SAYFASI =============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ api_name }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a, #1a1a2e, #16213e);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
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
        }
        .header p { color: #aaa; font-size: 1.1rem; margin-top: 10px; }
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
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stat-card .number {
            font-size: 2rem;
            font-weight: bold;
            color: #e94560;
        }
        .stat-card .label { color: #aaa; margin-top: 5px; }
        .endpoints {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .endpoint-card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }
        .endpoint-card:hover { border-color: #e94560; }
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
        .endpoint-card .path {
            font-size: 1.2rem;
            font-weight: bold;
            color: #fff;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .endpoint-card .desc { color: #aaa; font-size: 0.9rem; margin: 10px 0; }
        .endpoint-card .example {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            color: #8f8;
            overflow-x: auto;
            margin-top: 10px;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .feature {
            background: rgba(255,255,255,0.03);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .feature .icon { font-size: 2rem; margin-bottom: 5px; }
        .feature .name { color: #aaa; font-size: 0.9rem; }
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 40px;
        }
        .footer a { color: #e94560; text-decoration: none; }
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
            <p>Süper Güçlü CC Checker API</p>
            <span class="badge">v{{ version }}</span>
        </div>

        <div class="stats">
            <div class="stat-card"><div class="number">{{ total_endpoints }}</div><div class="label">📌 Endpoint</div></div>
            <div class="stat-card"><div class="number">{{ proxy_count }}</div><div class="label">🔄 Proxy</div></div>
            <div class="stat-card"><div class="number">8</div><div class="label">🔄 Deneme</div></div>
            <div class="stat-card"><div class="number">2</div><div class="label">🔧 Yöntem</div></div>
        </div>

        <h2 style="margin: 30px 0 20px 0; color: #e94560;">📡 Endpoint'ler</h2>
        <div class="endpoints">
            {% for endpoint in endpoints %}
            <div class="endpoint-card">
                <span class="method {{ endpoint.method.lower() }}">{{ endpoint.method }}</span>
                <div class="path">{{ endpoint.path }}</div>
                <div class="desc">{{ endpoint.description }}</div>
                <div class="example">
                    <div>URL: {{ endpoint.example.url }}</div>
                    {% if endpoint.example.body %}
                    <div>Body: {{ endpoint.example.body }}</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        <h2 style="margin: 30px 0 20px 0; color: #e94560;">⚡ Özellikler</h2>
        <div class="features">
            <div class="feature"><div class="icon">🛡️</div><div class="name">Cloudflare Bypass</div></div>
            <div class="feature"><div class="icon">🤖</div><div class="name">Googlebot Taklidi</div></div>
            <div class="feature"><div class="icon">🔄</div><div class="name">20+ Proxy</div></div>
            <div class="feature"><div class="icon">🔧</div><div class="name">2 İstek Yöntemi</div></div>
            <div class="feature"><div class="icon">⚡</div><div class="name">8 Deneme</div></div>
            <div class="feature"><div class="icon">🌍</div><div class="name">CORS Desteği</div></div>
        </div>

        <div class="footer">
            <p>💻 {{ api_name }} | © 2026 | <a href="{{ api_url }}">{{ api_url }}</a></p>
        </div>
    </div>
</body>
</html>
"""

# ============= ANA SAYFA =============
@app.route('/', methods=['GET'])
def home():
    endpoints = [
        {"method": "GET", "path": "/", "description": "API ana sayfası", "example": {"url": f"{API_URL}/"}},
        {"method": "GET", "path": "/api/generate", "description": "Rastgele kart üret", "example": {"url": f"{API_URL}/api/generate?count=5"}},
        {"method": "POST", "path": "/api/check-single", "description": "Tek kart kontrol", "example": {"url": f"{API_URL}/api/check-single", "body": '{"number":"4111111111111111","month":"12","year":"2026","cvv":"123"}'}},
        {"method": "POST", "path": "/api/check", "description": "Çoklu kart kontrol", "example": {"url": f"{API_URL}/api/check", "body": '{"cards":[{"number":"4111111111111111","month":"12","year":"2026","cvv":"123"}]}'}},
        {"method": "GET", "path": "/api/stats", "description": "API istatistikleri", "example": {"url": f"{API_URL}/api/stats"}},
        {"method": "GET", "path": "/api/health", "description": "API sağlık kontrolü", "example": {"url": f"{API_URL}/api/health"}},
        {"method": "GET", "path": "/api/validate", "description": "Kart numarası doğrulama", "example": {"url": f"{API_URL}/api/validate?number=4111111111111111"}},
        {"method": "GET", "path": "/api/types", "description": "Kart tipleri", "example": {"url": f"{API_URL}/api/types"}},
    ]
    
    return render_template_string(
        HTML_TEMPLATE,
        api_name=API_NAME,
        version=API_VERSION,
        api_url=API_URL,
        total_endpoints=len(endpoints),
        proxy_count=len(api_client.proxy_manager.proxies),
        endpoints=endpoints
    )

# ============= API ENDPOINT'LERİ =============

@app.route('/api/generate', methods=['GET'])
def generate_cards():
    try:
        count = request.args.get('count', default=1, type=int)
        count = min(max(count, 1), MAX_CARDS)
        
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/check-single', methods=['POST'])
def check_single_card():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        required = ['number', 'month', 'year', 'cvv']
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "message": f"Missing field: {field}"}), 400
        
        result = CCChecker.check_card(data)
        
        if result and result.get('status') == 'success':
            return jsonify({
                "status": "success",
                "result": result.get('result', {}),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Card check failed",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/check', methods=['POST'])
def check_multiple_cards():
    try:
        data = request.get_json()
        if not data or 'cards' not in data:
            return jsonify({"status": "error", "message": "No cards provided"}), 400
        
        cards = data.get('cards', [])
        if not isinstance(cards, list):
            return jsonify({"status": "error", "message": "Cards must be an array"}), 400
        
        if len(cards) > MAX_CARDS:
            return jsonify({"status": "error", "message": f"Max {MAX_CARDS} cards allowed"}), 400
        
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
            time.sleep(0.5)
        
        return jsonify({
            "status": "success",
            "total": len(results),
            "live_count": live_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify({
        "status": "success",
        "name": API_NAME,
        "version": API_VERSION,
        "api_url": API_URL,
        "proxy_count": len(api_client.proxy_manager.proxies),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/": "Ana sayfa",
            "/api/generate": "Kart üret",
            "/api/check-single": "Tek kart kontrol",
            "/api/check": "Çoklu kart kontrol",
            "/api/stats": "İstatistikler",
            "/api/health": "Sağlık kontrolü",
            "/api/validate": "Kart doğrulama",
            "/api/types": "Kart tipleri"
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
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

@app.route('/api/validate', methods=['GET'])
def validate_card():
    try:
        number = request.args.get('number', '')
        if not number:
            return jsonify({"status": "error", "message": "Card number required"}), 400
        
        number = re.sub(r'\s+', '', number)
        if not number.isdigit():
            return jsonify({"status": "error", "message": "Invalid card number"}), 400
        
        def luhn_check(card):
            digits = [int(d) for d in str(card)]
            odd = digits[-1::-2]
            even = digits[-2::-2]
            total = sum(odd)
            for d in even:
                total += sum([int(x) for x in str(d * 2)])
            return total % 10 == 0
        
        is_valid = luhn_check(number)
        
        card_type = "UNKNOWN"
        if number.startswith('4'):
            card_type = "VISA"
        elif number.startswith('5'):
            card_type = "MASTERCARD"
        elif number.startswith('3'):
            card_type = "AMEX"
        elif number.startswith('6'):
            card_type = "DISCOVER"
        
        return jsonify({
            "status": "success",
            "number": number,
            "length": len(number),
            "valid": is_valid,
            "type": card_type,
            "bin": number[:6],
            "last4": number[-4:],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/types', methods=['GET'])
def card_types():
    return jsonify({
        "status": "success",
        "types": {
            "VISA": {"prefix": "4", "length": [16]},
            "MASTERCARD": {"prefix": "5", "length": [16]},
            "AMEX": {"prefix": "3", "length": [15]},
            "DISCOVER": {"prefix": "6", "length": [16]},
        },
        "timestamp": datetime.now().isoformat()
    })

# ============= CORS DESTEĞİ =============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ============= HATA YÖNETİMİ =============
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": [
            "/", "/api/generate", "/api/check-single", "/api/check",
            "/api/stats", "/api/health", "/api/validate", "/api/types"
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
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀 {API_NAME}                                          ║
║   📡 {API_URL}                                             ║
║   🔧 Port: {port}                                           ║
║   🔄 Proxy: {len(api_client.proxy_manager.proxies)} adet    ║
║   📊 Version: {API_VERSION}                                 ║
║                                                              ║
║   ✅ API başarıyla başlatıldı!                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
