import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, request
from src.config import load_config
from src.lib.db import init_db

app = Flask(__name__)

# Load configuration from our central config directory
app.config.from_object(load_config())

# Initialize DB connection based on environment config
init_db()

# Mock data based on the PDF requirements
PRODUCTS = [
    {"id": 1, "name": "Classic Croissant", "price": 4.50, "image": "🥐", "description": "Flaky, buttery, and baked fresh daily."},
    {"id": 2, "name": "Decadent Chocolate Cake", "price": 35.00, "image": "🍰", "description": "Rich layers of dark chocolate ganache and moist sponge."},
    {"id": 3, "name": "Blueberry Muffins", "price": 3.75, "image": "🧁", "description": "Bursting with wild blueberries and a crumb topping."},
    {"id": 4, "name": "Artisan Cookies", "price": 2.50, "image": "🍪", "description": "Chewy chocolate chip cookies with sea salt."},
    {"id": 5, "name": "Fudge Brownies", "price": 4.00, "image": "🍫", "description": "Dense, gooey brownies made with premium cocoa."}
]

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
