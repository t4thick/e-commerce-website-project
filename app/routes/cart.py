from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from flask_login import current_user
import random
import string
from app import db
from app.models import MenuItem, Order, OrderItem

cart_bp = Blueprint('cart', __name__)


def generate_order_number():
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


@cart_bp.route('/cart/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    cart = session.get('cart', [])

    for cart_item in cart:
        if cart_item['id'] == item_id:
            cart_item['quantity'] += 1
            session['cart'] = cart
            return jsonify({'success': True, 'cart_count': sum(i['quantity'] for i in cart)})

    cart.append({
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'image_url': item.image_url,
        'quantity': 1
    })
    session['cart'] = cart

    return jsonify({'success': True, 'cart_count': sum(i['quantity'] for i in cart)})


@cart_bp.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    cart_count = sum(item['quantity'] for item in cart)
    return render_template('cart.html', cart=cart, total=total, cart_count=cart_count)


@cart_bp.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    quantity = int(request.form.get('quantity', 0))
    cart = session.get('cart', [])

    if quantity <= 0:
        cart = [item for item in cart if item['id'] != item_id]
    else:
        for item in cart:
            if item['id'] == item_id:
                item['quantity'] = quantity
                break

    session['cart'] = cart
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('main.home'))

    total = sum(item['price'] * item['quantity'] for item in cart)

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        order = Order(
            order_number=generate_order_number(),
            user_id=current_user.id if current_user.is_authenticated else None,
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            total=total,
            status='paid',
            payment_status='dev_mode'
        )
        db.session.add(order)
        db.session.flush()

        for cart_item in cart:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=cart_item['id'],
                name=cart_item['name'],
                price=cart_item['price'],
                quantity=cart_item['quantity']
            )
            db.session.add(order_item)

        db.session.commit()

        session['cart'] = []

        return redirect(url_for('cart.order_success', order_id=order.id))

    cart_count = sum(item['quantity'] for item in cart)
    return render_template('checkout.html', cart=cart, total=total, cart_count=cart_count)


@cart_bp.route('/order-success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_success.html', order=order)

