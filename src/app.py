import sys
import json
import uuid
import io
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

# Ensure the project root is on sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import qrcode
import mysql.connector
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from src.config import load_config
from src.lib.db import init_db


app = Flask(__name__)

# Load configuration from our central config directory
app.config.from_object(load_config())
app.secret_key = app.config.get('SECRET_KEY', 'dev-fallback-secret')

# Initialize DB connection based on environment config
init_db()

def get_db_connection():
    return mysql.connector.connect(
        host="100.48.217.125",
        port=3306,
        user="webuser",
        password="MyStrongPassword123!",
        database="testsite"
    )

# --- Encryption Serializer ---
serializer = URLSafeTimedSerializer(app.secret_key)

def encrypt_order_payload(order_id, amount, user):
    """Encrypts order details into a secure token string."""
    payload = {
        'order_id': order_id,
        'amount': f"{float(amount):.2f}",
        'user': user
    }
    return serializer.dumps(payload, salt='qr-payment-salt')

def decrypt_order_payload(token):
    """Decrypts and verifies order payload token. Returns dict or None if tampered/invalid."""
    try:
        # Valid for 1 hour (3600 seconds)
        data = serializer.loads(token, salt='qr-payment-salt', max_age=3600)
        return data
    except (BadSignature, SignatureExpired, Exception) as e:
        print(f"[Crypto Error] Decryption failed: {e}")
        return None

def get_bank_payment_url(order_id, amount, user):
    bank_base = app.config.get('BANK_PUBLIC_BASE', 'http://18.232.86.144:5000')
    token = encrypt_order_payload(order_id, amount, user)
    return f"{bank_base}/pay?data={token}"

# --- Data ---

USERS_FILE = Path(__file__).resolve().parent / 'data' / 'users.json'
with open(USERS_FILE, 'r') as f:
    USERS = json.load(f)

PRODUCTS = [
    {"id": 1, "name": "Classic Croissant", "price": 4.50, "image": "🥐", "description": "Flaky, buttery, and baked fresh daily."},
    {"id": 2, "name": "Decadent Chocolate Cake", "price": 35.00, "image": "🍰", "description": "Rich layers of dark chocolate ganache and moist sponge."},
    {"id": 3, "name": "Blueberry Muffins", "price": 3.75, "image": "🧁", "description": "Bursting with wild blueberries and a crumb topping."},
    {"id": 4, "name": "Artisan Cookies", "price": 2.50, "image": "🍪", "description": "Chewy chocolate chip cookies with sea salt."},
    {"id": 5, "name": "Fudge Brownies", "price": 4.00, "image": "🍫", "description": "Dense, gooey brownies made with premium cocoa."}
]

ORDERS = {}

def find_product(product_id):
    return next((p for p in PRODUCTS if p['id'] == product_id), None)

# --- Routes ---
@app.route("/testdb")
def testdb():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()



        cursor.execute("SELECT * FROM transactions")

        users = cursor.fetchall()

        cursor.close()
        conn.close()

        return str(users)

    except Exception as e:
        return str(e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    search_query = request.args.get('q', '').lower()
    if search_query:
        filtered_products = [
            p for p in PRODUCTS
            if search_query in p['name'].lower() or search_query in p['description'].lower()
        ]
    else:
        filtered_products = PRODUCTS
    return render_template('products.html', products=filtered_products, search_query=search_query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')



        user = next((u for u in USERS if u['username'] == username and u['password'] == password), None)

        if user:
            session['user'] = user['username']
            session['name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            next_page = request.args.get('next') or url_for('products')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/buy/<int:product_id>')
def buy(product_id):
    if 'user' not in session:
        flash('Please log in to make a purchase.', 'error')
        return redirect(url_for('login', next=url_for('buy', product_id=product_id)))

    product = find_product(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('products'))

    order_id = uuid.uuid4().hex[:10].upper()
    ORDERS[order_id] = {
        'order_id': order_id,
        'product_id': product['id'],
        'product_name': product['name'],
        'amount': product['price'],
        'user': session['user'],    
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO transactions
        (order_id, username, amount, status)
        VALUES (%s, %s, %s, %s)
        """, 
        (
            order_id,
            session['user'],
            product['price'],
            'PENDING'
        )
    )

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for
                (
    'checkout',
        orderid=order_id,
        amount=product['price'],
        user=session['user'],
        product_id=product['id']
))

@app.route('/checkout')
def checkout():
    order_id = request.args.get('orderid')
    amount = request.args.get('amount')
    user = request.args.get('user')
    product_id = request.args.get('product_id', type=int)

    if not all([order_id, amount, user]):
        flash('Invalid checkout link.', 'error')
        return redirect(url_for('products'))

    product = find_product(product_id) if product_id else None
    order = ORDERS.get(order_id)
    
    bank_payment_url = get_bank_payment_url(order_id, amount, user)

    return render_template(
        'checkout.html',
        order_id=order_id,
        amount=amount,
        user=user,
        product=product,
        order=order,
        bank_payment_url=bank_payment_url
    )

@app.route('/qr/<order_id>')
def generate_qr(order_id):
    order = ORDERS.get(order_id)
    if order:
        amount = order['amount']
        user = order['user']
    else:
        amount = request.args.get('amount', '0.00')
        user = request.args.get('user', 'guest')
    
    payment_url = get_bank_payment_url(order_id, amount, user)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payment_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#3d2c23", back_color="#ffffff")
    
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    
    return send_file(buf, mimetype='image/png')

@app.route('/pay')
def bank_pay_page():
    """Mock Banking App payment confirmation page (simulating external banking app)"""
    token = request.args.get('data')
    
    if not token:
        return render_template('bank_pay.html', error="Missing encrypted payload data (?data=...)")
        
    payload = decrypt_order_payload(token)
    if not payload:
        return render_template('bank_pay.html', error="Invalid or tampered payment link signature!")

    return render_template(
        'bank_pay.html',
        order_id=payload['order_id'],
        amount=payload['amount'],
        user=payload['user'],
        token=token
    )

# --- API Endpoints ---

@app.route('/api/order/status/<order_id>')
def order_status(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify({'order_id': order_id, 'status': order['status']})

@app.route('/api/order/confirm/<order_id>', methods=['POST'])
def order_confirm(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    order['status'] = 'paid'
    return jsonify({'order_id': order_id, 'status': 'paid', 'message': 'Payment confirmed'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
