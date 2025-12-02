from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import random
import string
from functools import wraps

from config import Config
from models import db, User, StaffCode, OTPToken, MenuItem, Order, OrderItem

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            flash('You need staff access to view this page.', 'error')
            return redirect(url_for('staff_portal'))
        return f(*args, **kwargs)
    return decorated_function

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_order_number():
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Initialize database and seed data
def init_db():
    with app.app_context():
        db.create_all()
        
        # Seed staff codes
        if not StaffCode.query.first():
            codes = [
                StaffCode(code='ADMIN2024', role='admin', max_uses=5),
                StaffCode(code='MANAGER2024', role='manager', max_uses=10),
                StaffCode(code='STAFF2024', role='staff', max_uses=50),
            ]
            db.session.add_all(codes)
        
        # Seed menu items with real food images
        if not MenuItem.query.first():
            items = [
                MenuItem(
                    name='Original Chicken Sandwich Combo',
                    description='Crispy chicken sandwich with lettuce, mayo, served with fries and a drink.',
                    price=7.99,
                    image_url='https://images.unsplash.com/photo-1606755962773-d324e0a13086?w=400&h=300&fit=crop',
                    category='combos',
                    popular=True
                ),
                MenuItem(
                    name='Classic Burger Combo',
                    description='Juicy beef patty with lettuce, tomato, pickles, fries and drink.',
                    price=8.99,
                    image_url='https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=300&fit=crop',
                    category='combos',
                    popular=True
                ),
                MenuItem(
                    name='BBQ Pulled Pork Combo',
                    description='Slow-cooked pulled pork with tangy BBQ sauce, coleslaw, fries and drink.',
                    price=9.99,
                    image_url='https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=400&h=300&fit=crop',
                    category='combos'
                ),
                MenuItem(
                    name='Crispy Chicken Tenders',
                    description='Hand-breaded golden chicken tenders with your choice of dipping sauce.',
                    price=8.99,
                    image_url='https://images.unsplash.com/photo-1562967914-608f82629710?w=400&h=300&fit=crop',
                    category='chicken',
                    popular=True
                ),
                MenuItem(
                    name='Nashville Hot Chicken',
                    description='Fiery Nashville-style hot chicken on a brioche bun with pickles.',
                    price=10.99,
                    image_url='https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400&h=300&fit=crop',
                    category='chicken',
                    spicy=True
                ),
                MenuItem(
                    name='Classic Wings (8pc)',
                    description='Crispy bone-in wings tossed in your choice of Buffalo, BBQ, or Honey Garlic.',
                    price=11.99,
                    image_url='https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=400&h=300&fit=crop',
                    category='chicken'
                ),
                MenuItem(
                    name='Chicken & Waffles',
                    description='Crispy fried chicken on fluffy Belgian waffles with maple syrup.',
                    price=12.99,
                    image_url='https://images.unsplash.com/photo-1504544750208-dc0358e63f7f?w=400&h=300&fit=crop',
                    category='chicken'
                ),
                MenuItem(
                    name='Crispy Fries',
                    description='Golden, crispy fries seasoned to perfection.',
                    price=3.99,
                    image_url='https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400&h=300&fit=crop',
                    category='sides',
                    popular=True
                ),
                MenuItem(
                    name='Mac & Cheese',
                    description='Creamy, cheesy mac and cheese made with three cheeses.',
                    price=4.99,
                    image_url='https://images.unsplash.com/photo-1543339494-b4cd4f7ba686?w=400&h=300&fit=crop',
                    category='sides'
                ),
                MenuItem(
                    name='Coleslaw',
                    description='Fresh, creamy coleslaw with a tangy dressing.',
                    price=2.99,
                    image_url='https://images.unsplash.com/photo-1625938145744-e380515399bf?w=400&h=300&fit=crop',
                    category='sides'
                ),
                MenuItem(
                    name='Fresh Lemonade',
                    description='Freshly squeezed lemonade, perfectly sweet and tangy.',
                    price=3.49,
                    image_url='https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=400&h=300&fit=crop',
                    category='drinks'
                ),
                MenuItem(
                    name='Sweet Tea',
                    description='Classic Southern sweet iced tea.',
                    price=2.49,
                    image_url='https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&h=300&fit=crop',
                    category='drinks'
                ),
                MenuItem(
                    name='Soft Drinks',
                    description='Coca-Cola, Sprite, Fanta, or Dr Pepper.',
                    price=1.99,
                    image_url='https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400&h=300&fit=crop',
                    category='drinks'
                ),
            ]
            db.session.add_all(items)
        
        db.session.commit()


# ============ ROUTES ============

@app.route('/')
def home():
    menu_items = MenuItem.query.filter_by(available=True).all()
    popular_items = MenuItem.query.filter_by(popular=True, available=True).limit(3).all()
    staff_count = User.query.filter(User.role.in_(['staff', 'manager', 'admin'])).count()
    order_count = Order.query.filter(Order.created_at >= datetime.utcnow().date()).count()
    
    cart = session.get('cart', [])
    cart_count = sum(item['quantity'] for item in cart)
    
    return render_template('home.html', 
                         menu_items=menu_items, 
                         popular_items=popular_items,
                         staff_count=staff_count,
                         order_count=order_count,
                         cart_count=cart_count)


@app.route('/menu')
def menu():
    category = request.args.get('category', 'all')
    if category == 'all':
        items = MenuItem.query.filter_by(available=True).all()
    else:
        items = MenuItem.query.filter_by(category=category, available=True).all()
    
    cart = session.get('cart', [])
    cart_count = sum(item['quantity'] for item in cart)
    
    return render_template('menu.html', items=items, category=category, cart_count=cart_count)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        login_type = request.form.get('login_type', 'customer')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Generate OTP
            otp = generate_otp()
            expires = datetime.utcnow() + timedelta(minutes=10)
            
            # Delete old OTPs
            OTPToken.query.filter_by(user_id=user.id).delete()
            
            # Create new OTP
            token = OTPToken(user_id=user.id, token=otp, expires_at=expires)
            db.session.add(token)
            db.session.commit()
            
            # Store user_id in session for OTP verification
            session['pending_user_id'] = user.id
            session['login_type'] = login_type
            session['dev_otp'] = otp  # Show OTP in dev mode
            
            return redirect(url_for('verify_otp'))
        
        flash('Invalid email or password.', 'error')
    
    return render_template('login.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    dev_otp = session.get('dev_otp')
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        token = OTPToken.query.filter_by(user_id=user_id, token=otp).first()
        
        if token and token.expires_at > datetime.utcnow():
            user = User.query.get(user_id)
            login_user(user)
            
            # Cleanup
            OTPToken.query.filter_by(user_id=user_id).delete()
            db.session.commit()
            session.pop('pending_user_id', None)
            session.pop('login_type', None)
            session.pop('dev_otp', None)
            
            flash(f'Welcome back, {user.name or user.email}!', 'success')
            
            if user.is_staff():
                return redirect(url_for('manager_dashboard'))
            return redirect(url_for('home'))
        
        flash('Invalid or expired OTP code.', 'error')
    
    return render_template('verify_otp.html', dev_otp=dev_otp)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        account_type = request.form.get('account_type', 'customer')
        staff_code = request.form.get('staff_code', '').upper()
        
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('signup.html')
        
        user = User(email=email, name=name, phone=phone, email_verified=True)
        user.set_password(password)
        
        # If staff registration, verify code
        if account_type == 'staff' and staff_code:
            code = StaffCode.query.filter_by(code=staff_code, active=True).first()
            if not code:
                flash('Invalid staff registration code.', 'error')
                return render_template('signup.html')
            if code.max_uses and code.uses >= code.max_uses:
                flash('This staff code has reached its maximum uses.', 'error')
                return render_template('signup.html')
            
            user.role = code.role
            code.uses += 1
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/staff-portal', methods=['GET', 'POST'])
@login_required
def staff_portal():
    if current_user.is_staff():
        return redirect(url_for('manager_dashboard'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').upper()
        
        staff_code = StaffCode.query.filter_by(code=code, active=True).first()
        
        if not staff_code:
            flash('Invalid staff code.', 'error')
        elif staff_code.max_uses and staff_code.uses >= staff_code.max_uses:
            flash('This code has reached its maximum uses.', 'error')
        else:
            current_user.role = staff_code.role
            staff_code.uses += 1
            db.session.commit()
            flash(f'You are now a {staff_code.role}!', 'success')
            return redirect(url_for('manager_dashboard'))
    
    return render_template('staff_portal.html')


@app.route('/manager')
@login_required
@staff_required
def manager_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    
    stats = {
        'total_orders': Order.query.count(),
        'pending': Order.query.filter(Order.status.in_(['pending', 'paid'])).count(),
        'preparing': Order.query.filter_by(status='preparing').count(),
        'ready': Order.query.filter_by(status='ready').count(),
        'revenue': db.session.query(db.func.sum(Order.total)).filter(Order.status != 'cancelled').scalar() or 0
    }
    
    return render_template('manager.html', orders=orders, stats=stats)


@app.route('/manager/order/<int:order_id>/status', methods=['POST'])
@login_required
@staff_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'paid', 'preparing', 'ready', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.order_number} updated to {new_status}.', 'success')
    
    return redirect(url_for('manager_dashboard'))


# ============ CART & CHECKOUT ============

@app.route('/cart/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    cart = session.get('cart', [])
    
    # Check if item already in cart
    for cart_item in cart:
        if cart_item['id'] == item_id:
            cart_item['quantity'] += 1
            session['cart'] = cart
            return jsonify({'success': True, 'cart_count': sum(i['quantity'] for i in cart)})
    
    # Add new item
    cart.append({
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'image_url': item.image_url,
        'quantity': 1
    })
    session['cart'] = cart
    
    return jsonify({'success': True, 'cart_count': sum(i['quantity'] for i in cart)})


@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    cart_count = sum(item['quantity'] for item in cart)
    return render_template('cart.html', cart=cart, total=total, cart_count=cart_count)


@app.route('/cart/update/<int:item_id>', methods=['POST'])
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
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('home'))
    
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Create order
        order = Order(
            order_number=generate_order_number(),
            user_id=current_user.id if current_user.is_authenticated else None,
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            total=total,
            status='paid',  # Dev mode - skip payment
            payment_status='dev_mode'
        )
        db.session.add(order)
        db.session.flush()
        
        # Add order items
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
        
        # Clear cart
        session['cart'] = []
        
        return redirect(url_for('order_success', order_id=order.id))
    
    cart_count = sum(item['quantity'] for item in cart)
    return render_template('checkout.html', cart=cart, total=total, cart_count=cart_count)


@app.route('/order-success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_success.html', order=order)


# ============ API ENDPOINTS ============

@app.route('/api/cart')
def api_cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return jsonify({
        'items': cart,
        'total': total,
        'count': sum(item['quantity'] for item in cart)
    })


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)

