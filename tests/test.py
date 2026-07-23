import pytest
from unittest.mock import patch, MagicMock
from src.app import app, encrypt_order_payload, decrypt_order_payload
from werkzeug.security import generate_password_hash

MOCK_USERS = [
    {'user_id': 1, 'username': 'admin', 'name': 'Admin User', 'password': generate_password_hash('adminpassword')}
]

MOCK_PRODUCTS = [
    {"product_id": 1, "id": 1, "name": "Classic Croissant", "price": "4.50", "image": "🥐", "description": "Flaky"},
    {"product_id": 2, "id": 2, "name": "Decadent Chocolate Cake", "price": "35.00", "image": "🍰", "description": "Rich layers"}
]

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client

def get_mock_db_connection():
    """Returns a MagicMock that simulates the MySQL connection and cursor"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Define side effects for fetchone/fetchall based on queries
    def mock_execute(query, params=None):
        query = query.upper()
        if "FROM USERS" in query:
            if params and params[0] == 'admin':
                mock_cursor.fetchone.return_value = MOCK_USERS[0]
            else:
                mock_cursor.fetchone.return_value = None
        elif "FROM PRODUCTS WHERE PRODUCT_ID" in query:
            pid = params[0]
            prod = next((p for p in MOCK_PRODUCTS if p['product_id'] == pid), None)
            mock_cursor.fetchone.return_value = prod
        elif "FROM PRODUCTS" in query:
            mock_cursor.fetchall.return_value = MOCK_PRODUCTS
            
        mock_cursor.lastrowid = 12345

    mock_cursor.execute.side_effect = mock_execute
    return mock_conn

@patch('src.app.get_db_connection')
def test_login(mock_get_db, client):
    """Test user login with valid and invalid credentials."""
    mock_get_db.return_value = get_mock_db_connection()
    
    # Invalid login
    res = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'})
    assert b'Invalid username or password' in res.data
    
    # Valid login
    res = client.post('/login', data={'username': 'admin', 'password': 'adminpassword'}, follow_redirects=True)
    assert b'Welcome back' in res.data

@patch('src.app.get_db_connection')
def test_cart_api(mock_get_db, client):
    """Test AJAX cart add and remove functionality."""
    mock_get_db.return_value = get_mock_db_connection()
    
    # Login first
    client.post('/login', data={'username': 'admin', 'password': 'adminpassword'})

    # Add item to cart
    res = client.post('/api/cart/add/1')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'Added' in data['message']

    # Test cart context in session
    with client.session_transaction() as sess:
        assert 1 in sess['cart']

    # Remove item from cart
    res = client.post('/api/cart/remove/0')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    
    with client.session_transaction() as sess:
        assert len(sess['cart']) == 0

@patch('src.app.get_db_connection')
def test_checkout_api(mock_get_db, client):
    """Test the AJAX checkout route and order creation."""
    mock_get_db.return_value = get_mock_db_connection()
    
    client.post('/login', data={'username': 'admin', 'password': 'adminpassword'})

    # Add item
    client.post('/api/cart/add/2')

    # Checkout
    res = client.post('/api/cart/checkout')
    assert res.status_code == 200
    data = res.get_json()
    
    assert data['success'] is True
    assert 'order_id' in data
    assert 'bank_payment_url' in data
    assert data['amount'] == 35.00
    
    # Verify cart was cleared
    with client.session_transaction() as sess:
        assert len(sess['cart']) == 0

def test_encryption_payload():
    """Test that the encryption for banking payload works securely."""
    order_id = 12345
    amount = 50.50
    user = "alice"
    
    token = encrypt_order_payload(order_id, amount, user)
    assert token is not None
    assert type(token) is str
    
    payload = decrypt_order_payload(token)
    assert payload is not None
    assert payload['order_id'] == order_id
    assert payload['amount'] == "50.50"
    assert payload['user'] == user
