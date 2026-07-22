# Sweetcrumb Pastries - Web Application Prototype

This repository contains the barebones Flask web application prototype for Sweetcrumb Pastries. It features a premium, responsive UI for an e-commerce pastry shop, including a beautiful Home Page and an interactive All Products page with search functionality.

This is currently a frontend-focused prototype; it uses mock data and does not have a database or payment processing backend implemented yet.

## Features
- **Premium Aesthetics:** Modern design with glassmorphism, responsive grid layouts, and micro-animations.
- **Home Page:** Engaging hero section leading customers to the shop.
- **Products Page:** Dynamic grid layout for displaying pastries.
- **Search Functionality:** Server-side filtering of products by name and description.

## Tech Stack
- **Backend:** Python 3.11, Flask
- **Frontend:** HTML5, Jinja2 Templates, Vanilla CSS

## Installation & Setup

Follow these instructions to run the application locally on your machine.

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/) installed on your system.

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/ecommerce-app.git
   cd ecommerce-app
   ```

2. **Create and activate a virtual environment**
   - **On Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **On macOS/Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python src/app.py
   ```

5. **View the site**
   Open your web browser and navigate to `http://127.0.0.1:5000` to view the Sweetcrumb Pastries prototype!

## Next Steps (Future Roadmap)
- Integrate a database (MySQL/SQLAlchemy) to manage products and orders.
- Implement the QR code payload generation for checkout.
- Build the payment status confirmation polling logic.
