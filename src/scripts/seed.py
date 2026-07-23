import sys
from pathlib import Path
import json

# Ensure the project root is on sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mysql.connector
from werkzeug.security import generate_password_hash

# Database connection
conn = mysql.connector.connect(
    host="44.197.208.126",
    user="webuser",
    password="MyStrongPassword123!",
    database="ecommercedb",
    connection_timeout=5
)
cursor = conn.cursor()

print("Connected to database. Resetting tables...")

# 1. Drop tables in correct order to respect foreign keys
cursor.execute("DROP TABLE IF EXISTS transaction_items")
cursor.execute("DROP TABLE IF EXISTS transactions")
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("DROP TABLE IF EXISTS products")

# 2. Recreate Tables
cursor.execute("""
    CREATE TABLE users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        name VARCHAR(100) NOT NULL,
        password VARCHAR(255) NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE products (
        product_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        image VARCHAR(10) NOT NULL,
        description TEXT NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        total_price DECIMAL(10,2) NOT NULL,
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_transactions_user
            FOREIGN KEY (user_id)
            REFERENCES users(user_id)
            ON DELETE CASCADE
    )
""")

cursor.execute("""
    CREATE TABLE transaction_items (
        transaction_item_id INT AUTO_INCREMENT PRIMARY KEY,
        transaction_id INT NOT NULL,
        product VARCHAR(255) NOT NULL,
        amount INT NOT NULL,
        product_price DECIMAL(10,2) NOT NULL,
        CONSTRAINT fk_transaction_items_transaction
            FOREIGN KEY (transaction_id)
            REFERENCES transactions(transaction_id)
            ON DELETE CASCADE
    )
""")
print("Tables created successfully.")

# 3. Seed Users
print("Seeding users...")
users = [
    {"username": "admin", "name": "Admin User", "password": "adminpassword"},
    {"username": "jdoe", "name": "John Doe", "password": "password123"},
    {"username": "asmith", "name": "Alice Smith", "password": "alice123"},
    {"username": "bjones", "name": "Bob Jones", "password": "bob123"}
]

for user in users:
    hashed_password = generate_password_hash(user["password"])
    cursor.execute(
        "INSERT INTO users (username, name, password) VALUES (%s, %s, %s)",
        (user["username"], user["name"], hashed_password)
    )
conn.commit()

# 4. Seed Products
print("Seeding products...")
products = [
    {"name": "Classic Croissant", "price": 4.50, "image": "🥐", "description": "Flaky, buttery, and baked fresh daily."},
    {"name": "Decadent Chocolate Cake", "price": 35.00, "image": "🍰", "description": "Rich layers of dark chocolate ganache and moist sponge."},
    {"name": "Blueberry Muffins", "price": 3.75, "image": "🧁", "description": "Bursting with wild blueberries and a crumb topping."},
    {"name": "Artisan Cookies", "price": 2.50, "image": "🍪", "description": "Chewy chocolate chip cookies with sea salt."},
    {"name": "Fudge Brownies", "price": 4.00, "image": "🍫", "description": "Dense, gooey brownies made with premium cocoa."}
]

for p in products:
    cursor.execute(
        "INSERT INTO products (name, price, image, description) VALUES (%s, %s, %s, %s)",
        (p["name"], p["price"], p["image"], p["description"])
    )
conn.commit()

# 5. Seed Transactions (from teammate's seed script)
print("Seeding transactions...")
cursor.execute("INSERT INTO transactions (user_id, total_price, status) VALUES (2, 675.00, 'Pending')")
transaction1 = cursor.lastrowid

cursor.execute("INSERT INTO transactions (user_id, total_price, status) VALUES (3, 500.00, 'paid')")
transaction2 = cursor.lastrowid

items = [
    (transaction1, "Chocolate Croissant", 2, 120.00),
    (transaction1, "Blueberry Danish", 1, 150.00),
    (transaction1, "Cinnamon Roll", 3, 95.00),
    (transaction2, "Cheese Tart", 2, 180.00),
    (transaction2, "Apple Turnover", 1, 140.00)
]

cursor.executemany(
    "INSERT INTO transaction_items (transaction_id, product, amount, product_price) VALUES (%s, %s, %s, %s)",
    items
)
conn.commit()

cursor.close()
conn.close()

print("Database seeded successfully.")
