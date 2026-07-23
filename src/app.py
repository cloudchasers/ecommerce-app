import sys
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
from werkzeug.security import check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from src.config import load_config
from src.lib.db import init_db

app = Flask(__name__)
app.config.from_object(load_config())
app.secret_key = app.config.get('SECRET_KEY', 'dev-fallback-secret')

# Initialize DB connection based on environment config
init_db()

def get_db_connection():
    return mysql.connector.connect(
        host="44.197.208.126",
        port=3306,
        user="webuser",
        password="MyStrongPassword123!",
        database="ecommercedb",
        connection_timeout=3
    )

# --- Encryption Serializer ---
serializer = URLSafeTimedSerializer(app.secret_key)

def encrypt_order_payload(order_id, amount, user):
    payload = {
        'order_id': order_id,
        'amount': f"{float(amount):.2f}",
        'user': user
    }
    return serializer.dumps(payload, salt='qr-payment-salt')

def decrypt_order_payload(token):
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

# --- Helper Functions ---
def get_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        if product:
            # Re-map product_id to id to maintain frontend compatibility
            product['id'] = product['product_id']
            product['price'] = float(product['price'])
        return product
    except Exception as e:
        print(f"DB Error getting product: {e}")
        return None

def get_all_products(search_query=''):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if search_query:
            query = "SELECT * FROM products WHERE name LIKE %s OR description LIKE %s"
            val = f"%{search_query}%"
            cursor.execute(query, (val, val))
        else:
            cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        for p in products:
            p['id'] = p['product_id']
            p['price'] = float(p['price'])
        return products
    except Exception as e:
        print(f"DB Error getting all products: {e}")
        return []

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    search_query = request.args.get('q', '').lower()
    filtered_products = get_all_products(search_query)
    return render_template('products.html', products=filtered_products, search_query=search_query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                session['user'] = user['username']
                session['name'] = user['name']
                flash(f'Welcome back, {user["name"]}!', 'success')
                next_page = request.args.get('next') or url_for('products')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            print(f"Login DB Error: {e}")
            flash('Database connection error. Please try again later.', 'error')
            
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
            prod = get_product(pid)
            if prod:
                cart_items.append({'index': i, 'product': prod})
                total += prod['price']
    return dict(global_cart_items=cart_items, global_cart_total=total)

@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
def api_add_to_cart(product_id):
    if 'user' not in session:
        return jsonify({'error': 'Please log in to add items to your cart.', 'redirect': url_for('login')}), 401

    product = get_product(product_id)
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
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to checkout.', 'redirect': url_for('login')}), 401
        
    cart_ids = session.get('cart', [])
    if not cart_ids:
        return jsonify({'error': 'Your cart is empty.'}), 400
        
    cart_items = []
    total = 0.0
    for pid in cart_ids:
        prod = get_product(pid)
        if prod:
            cart_items.append(prod)
            total += prod['price']
            
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert main transaction
        cursor.execute(
            """
            INSERT INTO transactions (user_id, total_price, status)
            VALUES (%s, %s, %s)
            """, 
            (session['user_id'], total, 'PENDING')
        )
        order_id = cursor.lastrowid
        
        # Insert items
        items_data = []
        for item in cart_items:
            # We assume amount=1 for each item in the cart array
            items_data.append((order_id, item['name'], 1, item['price']))
            
        cursor.executemany(
            """
            INSERT INTO transaction_items (transaction_id, product, amount, product_price)
            VALUES (%s, %s, %s, %s)
            """,
            items_data
        )
        conn.commit()
        cursor.close()
        conn.close()
        
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
    except Exception as e:
        print(f"Checkout DB Error: {e}")
        return jsonify({'error': 'Database error during checkout.'}), 500

@app.route('/api/cart/drawer')
def api_cart_drawer():
    return render_template('_drawer_content.html')

@app.route('/cart/add/<int:product_id>')
def add_to_cart(product_id):
    if 'user' not in session:
        flash('Please log in to add items to your cart.', 'error')
        return redirect(url_for('login', next=url_for('products')))

    product = get_product(product_id)
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
        cart.pop(index)
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
        prod = get_product(pid)
        if prod:
            cart_items.append({'index': i, 'product': prod})
            total += prod['price']
            
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
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
            prod = get_product(pid)
            if prod:
                cart_items.append(prod)
                total += prod['price']
                
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transactions (user_id, total_price, status) VALUES (%s, %s, %s)", (session['user_id'], total, 'PENDING'))
            order_id = cursor.lastrowid
            
            items_data = [(order_id, item['name'], 1, item['price']) for item in cart_items]
            cursor.executemany("INSERT INTO transaction_items (transaction_id, product, amount, product_price) VALUES (%s, %s, %s, %s)", items_data)
            conn.commit()
            cursor.close()
            conn.close()
            
            session['cart'] = []
            return redirect(url_for('checkout_pay', order_id=order_id))
        except Exception as e:
            print(f"Checkout POST DB Error: {e}")
            flash('Database error during checkout.', 'error')
            return redirect(url_for('cart'))
            
    return redirect(url_for('cart'))

@app.route('/checkout/<int:order_id>')
def checkout_pay(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (order_id,))
        orders = cursor.fetchall()
        order = orders[0] if orders else None
        
        if not order or order['user_id'] != session['user_id']:
            cursor.close()
            conn.close()
            flash('Order not found.', 'error')
            return redirect(url_for('products'))
            
        if order['status'] == 'paid':
            cursor.close()
            conn.close()
            return redirect(url_for('receipt', order_id=order_id))
            
        cursor.execute("SELECT * FROM transaction_items WHERE transaction_id = %s", (order_id,))
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format for template
        order['order_id'] = order['transaction_id']
        order['amount'] = float(order['total_price'])
        order['items'] = items
        
        bank_payment_url = get_bank_payment_url(order['order_id'], order['amount'], session['user'])

        return render_template('checkout.html', order=order, bank_payment_url=bank_payment_url)
    except Exception as e:
        print(f"DB Error: {e}")
        flash('Database error.', 'error')
        return redirect(url_for('products'))

@app.route('/receipt/<int:order_id>')
def receipt(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (order_id,))
        orders = cursor.fetchall()
        order = orders[0] if orders else None
        
        if not order or order['user_id'] != session['user_id']:
            cursor.close()
            conn.close()
            flash('Order not found.', 'error')
            return redirect(url_for('products'))
            
        cursor.execute("SELECT * FROM transaction_items WHERE transaction_id = %s", (order_id,))
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        order['order_id'] = order['transaction_id']
        order['amount'] = float(order['total_price'])
        order['items'] = items
        
        return render_template('receipt.html', order=order)
    except Exception as e:
        print(f"DB Error: {e}")
        return redirect(url_for('products'))

@app.route('/history')
def history():
    if 'user_id' not in session:
        flash('Please log in to view your history.', 'error')
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        orders = cursor.fetchall()
        
        cursor2 = conn.cursor(dictionary=True)
        for order in orders:
            order['order_id'] = order['transaction_id']
            order['amount'] = float(order['total_price'])
            cursor2.execute("SELECT * FROM transaction_items WHERE transaction_id = %s", (order['transaction_id'],))
            order['items'] = cursor2.fetchall()
            
        cursor2.close()
        cursor.close()
        conn.close()
        return render_template('history.html', orders=orders)
    except Exception as e:
        print(f"DB Error: {e}")
        return redirect(url_for('products'))

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

@app.route('/api/order/status/<int:order_id>')
def order_status(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM transactions WHERE transaction_id = %s", (order_id,))
        order = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        return jsonify({'order_id': order_id, 'status': order['status']})
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'error': 'DB Error'}), 500

@app.route('/api/order/confirm/<int:order_id>', methods=['POST'])
def order_confirm(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE transactions SET status = 'paid' WHERE transaction_id = %s", (order_id,))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Order not found'}), 404
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'order_id': order_id, 'status': 'paid', 'message': 'Payment confirmed'})
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'error': 'DB Error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
