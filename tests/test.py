import pytest
from src.app import app, USERS, PRODUCTS, encrypt_order_payload, decrypt_order_payload

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    # Use the test client
    with app.test_client() as client:
        yield client

def test_login(client):
    """Test user login with valid and invalid credentials."""
    # Invalid login
    res = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'})
    assert b'Invalid username or password' in res.data
    
    # Valid login
    user = USERS[0]
    res = client.post('/login', data={'username': user['username'], 'password': user['password']}, follow_redirects=True)
    assert b'Welcome back' in res.data

def test_cart_api(client):
    """Test AJAX cart add and remove functionality."""
    user = USERS[0]
    client.post('/login', data={'username': user['username'], 'password': user['password']})

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

def test_checkout_api(client):
    """Test the AJAX checkout route and order creation."""
    user = USERS[0]
    client.post('/login', data={'username': user['username'], 'password': user['password']})

    # Add item
    client.post('/api/cart/add/2')

    # Checkout
    res = client.post('/api/cart/checkout')
    assert res.status_code == 200
    data = res.get_json()
    
    assert data['success'] is True
    assert 'order_id' in data
    assert 'bank_payment_url' in data
    assert data['amount'] == 35.00  # product 2 price
    
    # Verify cart was cleared
    with client.session_transaction() as sess:
        assert len(sess['cart']) == 0

def test_encryption_payload():
    """Test that the encryption for banking payload works securely."""
    order_id = "TEST-ORDER-123"
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
