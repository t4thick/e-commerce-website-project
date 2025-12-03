import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def setup_logging(app):
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        'logs/crispy_cluckers.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('Crispy Cluckers startup')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Setup logging
    setup_logging(app)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.cart import cart_bp
    from app.routes.manager import manager_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(cart_bp)
    app.register_blueprint(manager_bp)

    with app.app_context():
        from app.models import User, MenuItem, StaffCode
        db.create_all()
        seed_data()

    return app


def seed_data():
    from app.models import MenuItem, StaffCode

    if not StaffCode.query.first():
        codes = [
            StaffCode(code='ADMIN2024', role='admin', max_uses=5),
            StaffCode(code='MANAGER2024', role='manager', max_uses=10),
            StaffCode(code='STAFF2024', role='staff', max_uses=50),
        ]
        db.session.add_all(codes)
        db.session.commit()

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
        ]
        db.session.add_all(items)
        db.session.commit()

