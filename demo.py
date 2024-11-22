# # Add to Cart route
# @app.route('/add_to_cart/<int:product_id>', methods=['POST'])
# @login_required
# def add_to_cart(product_id):
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
#     # Check if the product exists
#     cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
#     product = cursor.fetchone()
#     if not product:
#         flash('Product not found!', 'danger')
#         return redirect(url_for('home'))

#     # Check if the item is already in the user's cart
#     cursor.execute(
#         'SELECT * FROM cart WHERE user_id = %s AND product_id = %s', 
#         (current_user.id, product_id)
#     )
#     cart_item = cursor.fetchone()

#     if cart_item:
#         # Update quantity if product already exists in cart
#         cursor.execute(
#             'UPDATE cart SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s',
#             (current_user.id, product_id)
#         )
#     else:
#         # Insert new product into cart
#         cursor.execute(
#             'INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)',
#             (current_user.id, product_id, 1)
#         )
#     mysql.connection.commit()
#     flash(f'{product["name"]} added to cart!', 'success')
#     return redirect(url_for('home'))



# # View Cart route
# @app.route('/cart')
# @login_required
# def view_cart():
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
#     # Fetch user's cart items
#     cursor.execute('''
#         SELECT c.id AS cart_id, p.id AS product_id, p.name, p.price, c.quantity, p.image 
#         FROM cart c
#         JOIN products p ON c.product_id = p.id
#         WHERE c.user_id = %s
#     ''', (current_user.id,))
#     cart_items = cursor.fetchall()

#     # Calculate the total price
#     total = sum(item['price'] * item['quantity'] for item in cart_items)
#     return render_template('cart.html', cart_items=cart_items, total=total)


# # Remove Item from Cart
# @app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
# @login_required
# def remove_from_cart(cart_id):
#     cursor = mysql.connection.cursor()
    
#     # Remove item from cart
#     cursor.execute('DELETE FROM cart WHERE id = %s AND user_id = %s', (cart_id, current_user.id))
#     mysql.connection.commit()
#     flash('Item removed from cart.', 'success')
#     return redirect(url_for('view_cart'))


# # Stripe Checkout route
# @app.route('/create-checkout-session', methods=['POST'])
# @login_required
# def create_checkout_session():
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
#     # Fetch user's cart items
#     cursor.execute('''
#         SELECT p.name, p.price, c.quantity 
#         FROM cart c
#         JOIN products p ON c.product_id = p.id
#         WHERE c.user_id = %s
#     ''', (current_user.id,))
#     cart_items = cursor.fetchall()

#     if not cart_items:
#         flash('Your cart is empty!', 'warning')
#         return redirect(url_for('view_cart'))

#     # Create Stripe line items
#     line_items = [
#         {
#             'price_data': {
#                 'currency': 'inr',
#                 'product_data': {'name': item['name']},
#                 'unit_amount': int(item['price'] * 100),
#             },
#             'quantity': item['quantity'],
#         }
#         for item in cart_items
#     ]

#     try:
#         checkout_session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             line_items=line_items,
#             mode='payment',
#             success_url=url_for('payment_success', _external=True),
#             cancel_url=url_for('view_cart', _external=True),
#         )
#         return redirect(checkout_session.url, code=303)
#     except Exception as e:
#         flash(f'Error creating Stripe session: {e}', 'danger')
#         return redirect(url_for('view_cart'))


# @app.route('/success')
# @login_required
# def payment_success():
#     cursor = mysql.connection.cursor()
    
#     # Clear the user's cart after successful payment
#     cursor.execute('DELETE FROM cart WHERE user_id = %s', (current_user.id,))
#     mysql.connection.commit()

#     flash('Payment successful! Thank you for your purchase.', 'success')
#     return redirect(url_for('home'))




# cart.html


# <!DOCTYPE html>
# <html>
# <head>
#     <title>Your Cart</title>
# </head>
# <body>
#     <h1>Your Cart</h1>
#     {% if cart_items %}
#         <table>
#             <tr>
#                 <th>Product</th>
#                 <th>Quantity</th>
#                 <th>Price</th>
#                 <th>Total</th>
#                 <th>Actions</th>
#             </tr>
#             {% for item in cart_items %}
#             <tr>
#                 <td>{{ item.name }}</td>
#                 <td>{{ item.quantity }}</td>
#                 <td>₹{{ item.price }}</td>
#                 <td>₹{{ item.quantity * item.price }}</td>
#                 <td>
#                     <form action="/remove_from_cart/{{ item.cart_id }}" method="POST">
#                         <button type="submit">Remove</button>
#                     </form>
#                 </td>
#             </tr>
#             {% endfor %}
#         </table>
#         <p><strong>Total: ₹{{ total }}</strong></p>
#         <form action="/create-checkout-session" method="POST">
#             <button type="submit">Checkout with Stripe</button>
#         </form>
#     {% else %}
#         <p>Your cart is empty.</p>
#     {% endif %}
# </body>
# </html>
