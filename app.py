from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import MySQLdb.cursors
import stripe


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PORT'] = 3000
app.config['MYSQL_PASSWORD'] = 'VkapsIT'
app.config['MYSQL_DB'] = 'amazon_clone'

stripe.api_key = "sk_test_51NFtVGSAZAXtdYSkBaDemNewFODLyLvAZ4Cp8oCxI2m1ecvfG2C1cNpm1B6k6lwIQfD2f9Hxt53gG2hNGExnFVK100raNTKWo4"

# Initialize extensions
mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name  # Add name to the User class


@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return User(user_data['id'], user_data['email'], user_data['name'])  # Load name as well
    return None


# Home route
@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Example static data for products
    products = [
        {"id": 1, "name": "Perfume", "description": "Long-lasting fragrance", "price": 499, "image": "product1.jpg"},
        {"id": 2, "name": "Sunglasses", "description": "Stylish and UV-protected", "price": 799, "image": "product2.jpg"},
        {"id": 3, "name": "Watch", "description": "Elegant wristwatch", "price": 999, "image": "product3.jpg"},
        {"id": 4, "name": "Handbag", "description": "Leather handbag", "price": 499, "image": "product4.jpg"},
        {"id": 5, "name": "Shoes", "description": "Comfortable running shoes", "price": 1299, "image": "product5.jpg"},
        {"id": 6, "name": "Headphones", "description": "Noise-cancelling headphones", "price": 2499, "image": "product6.jpg"},
        {"id": 7, "name": "Laptop Bag", "description": "Durable laptop bag", "price": 999, "image": "product7.jpg"},
        {"id": 8, "name": "T-shirt", "description": "Cotton T-shirt", "price": 499, "image": "product8.jpg"},
        {"id": 9, "name": "Camera", "description": "DSLR Camera", "price": 34999, "image": "product9.jpg"},
        {"id": 10, "name": "Smartphone", "description": "Latest model smartphone", "price": 59999, "image": "product10.jpg"},
    ]

    # Fetch the average rating for each product
    for product in products:
        cursor.execute('SELECT AVG(rating) AS avg_rating FROM reviews WHERE product_id = %s', (product['id'],))
        avg_rating = cursor.fetchone()['avg_rating']
        product['average_rating'] = avg_rating if avg_rating is not None else 0

    return render_template('home.html', products=products)

# Add to Cart
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if the product exists
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('home'))

    # Check if the item is already in the user's cart
    cursor.execute(
        'SELECT * FROM cart WHERE user_id = %s AND product_id = %s', 
        (current_user.id, product_id)
    )
    cart_item = cursor.fetchone()

    if cart_item:
        # Update quantity if product already exists in cart
        cursor.execute(
            'UPDATE cart SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s',
            (current_user.id, product_id)
        )
    else:
        # Insert new product into cart
        cursor.execute(
            'INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)',
            (current_user.id, product_id, 1)
        )
    mysql.connection.commit()
    flash(f'{product["name"]} added to cart!', 'success')
    return redirect(url_for('home'))


@app.route('/cart', methods=['GET'])
@login_required
def view_cart():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch items in the cart for the logged-in user
    cursor.execute('''
        SELECT cart.id AS cart_item_id, products.name, products.price, cart.quantity 
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = %s
    ''', (current_user.id,))
    cart_items = cursor.fetchall()

    # Calculate total price
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


# @app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
# @login_required
# def remove_from_cart(product_id):
#     cursor = mysql.connection.cursor()
    
#     # Remove item from cart
#     cursor.execute('DELETE FROM cart WHERE id = %s AND user_id = %s', (product_id, current_user.id))
#     mysql.connection.commit()
#     flash('Item removed from cart.', 'success')
#     return redirect(url_for('view_cart'))



# Stripe Checkout route
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch user's cart items
    cursor.execute(''' 
        SELECT p.name, p.price, c.quantity 
        FROM cart c
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = %s
    ''', (current_user.id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('view_cart'))

    # Fetch customer details (e.g., name, address) from user profile
    cursor.execute(''' 
        SELECT name, address, city, state, postal_code, country 
        FROM users 
        WHERE id = %s
    ''', (current_user.id,))
    user_info = cursor.fetchone()

    # Ensure that user_info contains necessary details
    if not user_info or not user_info['name'] or not user_info['address']:
        flash('Customer name and address are required for export transactions.', 'danger')
        return redirect(url_for('view_cart'))

    # Create Stripe line items
    line_items = [
        {
            'price_data': {
                'currency': 'inr',
                'product_data': {'name': item['name']},
                'unit_amount': int(item['price'] * 100),
            },
            'quantity': item['quantity'],
        }
        for item in cart_items
    ]

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('payment_success', _external=True),
            cancel_url=url_for('view_cart', _external=True),
            customer_email=current_user.email,  # Customer's email
            shipping_address_collection={
                'allowed_countries': ['IN'],  # Collect shipping address for Indian customers
            },
            shipping_options=[{
                'shipping_rate_data': {
                    'type': 'fixed_amount',
                    'fixed_amount': {'amount': 0, 'currency': 'inr'},
                    'delivery_estimate': {
                        'minimum': {'unit': 'hour', 'value': 1},
                        'maximum': {'unit': 'hour', 'value': 3},
                    },
                    'display_name': 'Standard Shipping',  # Add display_name for the shipping rate
                },
            }],
            # No need for `customer_name` and `customer_address`
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Error creating Stripe session: {e}', 'danger')
        return redirect(url_for('view_cart'))


@app.route('/checkout')
@login_required
def checkout():
    # Fetch user's cart items again to display them on the checkout page
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(''' 
        SELECT p.name, p.price, c.quantity 
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    ''', (current_user.id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('view_cart'))

    # Render the checkout page (you can create a checkout.html template)
    return render_template('checkout.html', cart_items=cart_items)


@app.route('/success')
@login_required
def payment_success():
    cursor = mysql.connection.cursor()
    
    # Clear the user's cart after successful payment
    cursor.execute('DELETE FROM cart WHERE user_id = %s', (current_user.id,))
    mysql.connection.commit()

    flash('Payment successful! Thank you for your purchase.', 'success')
    return redirect(url_for('home'))



# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Capture the user's input
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        postal_code = request.form['postal_code']
        country = request.form['country']

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert data into the users table
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password, address, city, state, postal_code, country) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, email, hashed_password, address, city, state, postal_code, country))  # Insert all fields
        mysql.connection.commit()

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')



# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # Pass the name along with id and email
            login_user(User(user['id'], user['email'], user['name']))
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')


# Product page with rating and reviews
@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_page(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch product details
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()

    # Fetch reviews along with user names
    cursor.execute('''
        SELECT r.rating, r.review, u.name 
        FROM reviews r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.product_id = %s
    ''', (product_id,))
    reviews = cursor.fetchall()

    # Initialize existing_review to None by default
    existing_review = None

    # Check if the user is authenticated and if they have already reviewed the product
    if current_user.is_authenticated:
        cursor.execute('SELECT * FROM reviews WHERE product_id = %s AND user_id = %s', 
                       (product_id, current_user.id))
        existing_review = cursor.fetchone()

    # Calculate average rating for the product
    cursor.execute('SELECT AVG(rating) AS avg_rating FROM reviews WHERE product_id = %s', (product_id,))
    avg_rating = cursor.fetchone()['avg_rating']

    # If there are no reviews, set the average rating to 0
    product['average_rating'] = avg_rating if avg_rating is not None else 0

    if request.method == 'POST':
        if current_user.is_authenticated:
            rating = request.form['rating']
            review = request.form['review']
            user_id = current_user.id

            if existing_review:
                flash('You have already reviewed this product!', 'danger')
                return redirect(url_for('product_page', product_id=product_id))

            # Insert the new review
            cursor.execute('INSERT INTO reviews (product_id, user_id, rating, review) VALUES (%s, %s, %s, %s)', 
                           (product_id, user_id, rating, review))
            mysql.connection.commit()
            flash('Review submitted successfully!', 'success')
            return redirect(url_for('product_page', product_id=product_id))

        else:
            flash('You need to be logged in to submit a review', 'warning')
            return redirect(url_for('login'))

    return render_template('product.html', product=product, reviews=reviews, existing_review=existing_review)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route('/save-card', methods=['POST'])
@login_required
def save_card():
    # Get the token from the client-side
    data = request.get_json()
    token = data['token']
    
    # Use the token to create a Stripe customer
    try:
        # Create a customer in Stripe (you can also create one beforehand if you prefer)
        customer = stripe.Customer.create(
            email=current_user.email,
            source=token  # This is the tokenized card data
        )
        
        # Store customer ID and token in your database (NOT the card details)
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO payment_methods (user_id, stripe_customer_id, stripe_token)
            VALUES (%s, %s, %s)
        ''', (current_user.id, customer.id, token))
        mysql.connection.commit()
        
        return jsonify({"message": "Card successfully saved"}), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400



 
if __name__ == '__main__':
    app.run(debug=True)
