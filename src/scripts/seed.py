import bcrypt
import mysql.connector

# Database connection
conn = mysql.connector.connect(
    host="44.197.208.126",
    user="webuser",
    password="MyStrongPassword123!",
    database="ecommercedb"
)

cursor = conn.cursor()

# ------------------------------------------------------------------
# Create tables if they do not exist
# ------------------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
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
CREATE TABLE IF NOT EXISTS transaction_items (
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

conn.commit()

# ------------------------------------------------------------------
# Seed users (3 consumers + 1 merchant)
# ------------------------------------------------------------------

users = [
    {
        "username": "jdoe",
        "name": "John Doe",
        "password": "password123"
    },
    {
        "username": "asmith",
        "name": "Alice Smith",
        "password": "alice123"
    },
    {
        "username": "bjones",
        "name": "Bob Jones",
        "password": "bob123"
    },
    {
        "username": "merchant",
        "name": "E-Commerce Merchant",
        "password": "merchant123"
    }
]

for user in users:

    cursor.execute(
        "SELECT user_id FROM users WHERE username = %s",
        (user["username"],)
    )

    existing_user = cursor.fetchone()

    if not existing_user:
        hashed_password = bcrypt.hashpw(
            user["password"].encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users (username, name, password)
            VALUES (%s, %s, %s)
            """,
            (
                user["username"],
                user["name"],
                hashed_password
            )
        )

conn.commit()

# ------------------------------------------------------------------
# Get user IDs
# ------------------------------------------------------------------

cursor.execute(
    "SELECT user_id FROM users WHERE username = 'jdoe'"
)
john_id = cursor.fetchone()[0]

cursor.execute(
    "SELECT user_id FROM users WHERE username = 'asmith'"
)
alice_id = cursor.fetchone()[0]

# ------------------------------------------------------------------
# Seed Transaction 1
# ------------------------------------------------------------------

cursor.execute("""
SELECT transaction_id
FROM transactions
WHERE user_id = %s
AND total_price = %s
AND status = %s
""", (john_id, 675.00, "Pending"))

row = cursor.fetchone()

if row:
    transaction1 = row[0]
else:
    cursor.execute("""
        INSERT INTO transactions (
            user_id,
            total_price,
            status
        )
        VALUES (%s, %s, %s)
    """, (john_id, 675.00, "Pending"))

    transaction1 = cursor.lastrowid

# ------------------------------------------------------------------
# Seed Transaction 2
# ------------------------------------------------------------------

cursor.execute("""
SELECT transaction_id
FROM transactions
WHERE user_id = %s
AND total_price = %s
AND status = %s
""", (alice_id, 500.00, "Completed"))

row = cursor.fetchone()

if row:
    transaction2 = row[0]
else:
    cursor.execute("""
        INSERT INTO transactions (
            user_id,
            total_price,
            status
        )
        VALUES (%s, %s, %s)
    """, (alice_id, 500.00, "Completed"))

    transaction2 = cursor.lastrowid

conn.commit()

# ------------------------------------------------------------------
# Seed Transaction Items
# ------------------------------------------------------------------

items = [
    (transaction1, "Chocolate Croissant", 2, 120.00),
    (transaction1, "Blueberry Danish", 1, 150.00),
    (transaction1, "Cinnamon Roll", 3, 95.00),
    (transaction2, "Cheese Tart", 2, 180.00),
    (transaction2, "Apple Turnover", 1, 140.00)
]

for item in items:

    cursor.execute("""
        SELECT transaction_item_id
        FROM transaction_items
        WHERE transaction_id = %s
        AND product = %s
        AND amount = %s
        AND product_price = %s
    """, item)

    existing_item = cursor.fetchone()

    if not existing_item:
        cursor.execute("""
            INSERT INTO transaction_items (
                transaction_id,
                product,
                amount,
                product_price
            )
            VALUES (%s, %s, %s, %s)
        """, item)

conn.commit()

cursor.close()
conn.close()

print("Database seeded successfully. Existing records were skipped.")