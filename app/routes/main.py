import logging
from flask import Blueprint, render_template, request, session
from flask_login import current_user
from datetime import datetime
from app.models import MenuItem, User, Order

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    logger.debug('Home page accessed')
    menu_items = MenuItem.query.filter_by(available=True).all()
    popular_items = MenuItem.query.filter_by(popular=True, available=True).limit(3).all()
    staff_count = User.query.filter(User.role.in_(['staff', 'manager', 'admin'])).count()
    order_count = Order.query.filter(Order.created_at >= datetime.utcnow().date()).count()

    cart = session.get('cart', [])
    cart_count = sum(item['quantity'] for item in cart)

    logger.info(f'Home page loaded - {len(menu_items)} items, {order_count} orders today')
    
    return render_template(
        'home.html',
        menu_items=menu_items,
        popular_items=popular_items,
        staff_count=staff_count,
        order_count=order_count,
        cart_count=cart_count
    )


@main_bp.route('/menu')
def menu():
    category = request.args.get('category', 'all')

    if category == 'all':
        items = MenuItem.query.filter_by(available=True).all()
    else:
        items = MenuItem.query.filter_by(category=category, available=True).all()

    cart = session.get('cart', [])
    cart_count = sum(item['quantity'] for item in cart)

    return render_template('menu.html', items=items, category=category, cart_count=cart_count)

