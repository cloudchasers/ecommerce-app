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
    return f"{bank_base}/?data={token}"

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

ORDERS_FILE = Path(__file__).resolve().parent / 'data' / 'orders.json'
if ORDERS_FILE.exists():
    with open(ORDERS_FILE, 'r') as f:
        try:
            ORDERS = json.load(f)
        except json.JSONDecodeError:
            ORDERS = {}
else:
    ORDERS = {}

def save_orders():
    with open(ORDERS_FILE, 'w') as f:
        json.dump(ORDERS, f, indent=4)

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

@app.context_processor
def inject_cart_data():
    cart_items = []
    total = 0.0
    if 'cart' in session:
        for i, pid in enumerate(session['cart']):
            prod = find_product(pid)
            if prod:
                cart_items.append({'index': i, 'product': prod})
                total += prod['price']
    return dict(global_cart_items=cart_items, global_cart_total=total)

@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
def api_add_to_cart(product_id):
    if 'user' not in session:
        return jsonify({'error': 'Please log in to add items to your cart.', 'redirect': url_for('login')}), 401

    product = find_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found.'}), 404
        
    cart = session.get('cart', [])
    cart.append(product['id'])
    session['cart'] = cart
    return jsonify({'success': True, 'message': f'Added {product["name"]} to your cart!'})

@app.route('/api/cart/remove/<int:index>', methods=['POST'])
def api_remove_from_cart(index):
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session['cart'] = cart
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid index.'}), 400

@app.route('/api/cart/checkout', methods=['POST'])
def api_checkout():
    if 'user' not in session:
        return jsonify({'error': 'Please log in to checkout.', 'redirect': url_for('login')}), 401
        
    cart_ids = session.get('cart', [])
    if not cart_ids:
        return jsonify({'error': 'Your cart is empty.'}), 400
        
    cart_items = []
    total = 0.0
    for pid in cart_ids:
        prod = find_product(pid)
        if prod:
            cart_items.append({'id': prod['id'], 'name': prod['name'], 'price': prod['price'], 'image': prod['image']})
            total += prod['price']
            
    order_id = uuid.uuid4().hex[:10].upper()
    ORDERS[order_id] = {
        'order_id': order_id,
                'items': cart_items,
        'amount': total,
        'user': session['user'],
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    save_orders()
    
    # --- Angelica's MySQL DB Tracking (Safely Integrated) ---
    try:
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
                total,
                'PENDING'
            )
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to log to MySQL database: {e}")
        # We don't want the checkout to fail for the user just because the DB is unreachable 
        # (especially important for Jenkins tests to pass)
    
    # Clear cart
    session['cart'] = []
    
    bank_payment_url = get_bank_payment_url(order_id, total, session['user'])
    
    return jsonify({
        'success': True,
        'order_id': order_id,
        'amount': total,
        'items': cart_items,
        'bank_payment_url': bank_payment_url
    })

@app.route('/api/cart/drawer')
def api_cart_drawer():
    return render_template('_drawer_content.html')

@app.route('/cart/add/<int:product_id>')
def add_to_cart(product_id):
    if 'user' not in session:
        flash('Please log in to add items to your cart.', 'error')
        return redirect(url_for('login', next=url_for('products')))

    product = find_product(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('products'))
        
    cart = session.get('cart', [])
    cart.append(product['id'])
    session['cart'] = cart
    flash(f'Added {product["name"]} to your cart!', 'success')
    return redirect(url_for('products'))

@app.route('/cart/remove/<int:index>')
def remove_from_cart(index):
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        removed_id = cart.pop(index)
        session['cart'] = cart
        flash('Item removed from cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user' not in session:
        flash('Please log in to view your cart.', 'error')
        return redirect(url_for('login'))
        
    cart_ids = session.get('cart', [])
    cart_items = []
    total = 0.0
    for i, pid in enumerate(cart_ids):
        prod = find_product(pid)
        if prod:
            cart_items.append({'index': i, 'product': prod})
            total += prod['price']
            
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session:
        flash('Please log in to checkout.', 'error')
        return redirect(url_for('login'))
        
    cart_ids = session.get('cart', [])
    if not cart_ids:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('products'))
        
    if request.method == 'POST':
        # Create order
        cart_items = []
        total = 0.0
        for pid in cart_ids:
            prod = find_product(pid)
            if prod:
                cart_items.append({'id': prod['id'], 'name': prod['name'], 'price': prod['price'], 'image': prod['image']})
                total += prod['price']
                
        order_id = uuid.uuid4().hex[:10].upper()
        ORDERS[order_id] = {
            'order_id': order_id,
            'items': cart_items,
            'amount': total,
            'user': session['user'],
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        save_orders()
        
        # Clear cart
        session['cart'] = []
        return redirect(url_for('checkout_pay', order_id=order_id))
        
    return redirect(url_for('cart'))

@app.route('/checkout/<order_id>')
def checkout_pay(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    order = ORDERS.get(order_id)
    if not order or order['user'] != session['user']:
        flash('Order not found.', 'error')
        return redirect(url_for('products'))
        
    if order['status'] == 'paid':
        return redirect(url_for('receipt', order_id=order_id))
        
    bank_payment_url = get_bank_payment_url(order_id, order['amount'], order['user'])

    return render_template(
        'checkout.html',
        order=order,
        bank_payment_url=bank_payment_url
    )

@app.route('/receipt/<order_id>')
def receipt(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    order = ORDERS.get(order_id)
    if not order or order['user'] != session['user']:
        flash('Order not found.', 'error')
        return redirect(url_for('products'))
        
    return render_template('receipt.html', order=order)

@app.route('/history')
def history():
    if 'user' not in session:
        flash('Please log in to view your history.', 'error')
        return redirect(url_for('login'))
        
    user_orders = [o for o in ORDERS.values() if o['user'] == session['user']]
    # Sort by created_at descending
    user_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('history.html', orders=user_orders)



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
    save_orders()
    return jsonify({'order_id': order_id, 'status': 'paid', 'message': 'Payment confirmed'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
