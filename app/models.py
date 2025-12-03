from datetime import datetime
import logging
import bcrypt
from flask_login import UserMixin
from app import db, login_manager

logger = logging.getLogger(__name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='customer')
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )

    def is_staff(self):
        return self.role in ['staff', 'manager', 'admin']


class StaffCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), default='staff')
    uses = db.Column(db.Integer, default=0)
    max_uses = db.Column(db.Integer, nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OTPToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50))
    popular = db.Column(db.Boolean, default=False)
    spicy = db.Column(db.Boolean, default=False)
    available = db.Column(db.Boolean, default=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')
    total = db.Column(db.Float, nullable=False)
    payment_id = db.Column(db.String(100))
    payment_status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Real-time tracking timestamps
    paid_at = db.Column(db.DateTime)
    preparing_at = db.Column(db.DateTime)
    ready_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    estimated_ready_minutes = db.Column(db.Integer, default=15)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    tracking_events = db.relationship('OrderTracking', backref='order', lazy=True, cascade='all, delete-orphan', order_by='OrderTracking.created_at')
    
    def update_status(self, new_status, notes=None):
        """Update order status with timestamp tracking"""
        old_status = self.status
        self.status = new_status
        now = datetime.utcnow()
        
        # Set specific timestamp based on status
        if new_status == 'paid':
            self.paid_at = now
        elif new_status == 'preparing':
            self.preparing_at = now
        elif new_status == 'ready':
            self.ready_at = now
        elif new_status == 'completed':
            self.completed_at = now
        
        # Create tracking event
        tracking = OrderTracking(
            order_id=self.id,
            status=new_status,
            notes=notes
        )
        db.session.add(tracking)
        
        logger.info(f'Order {self.order_number} status changed: {old_status} -> {new_status}')
        return tracking
    
    def get_elapsed_time(self):
        """Get elapsed time since order was created"""
        delta = datetime.utcnow() - self.created_at
        return int(delta.total_seconds())
    
    def get_progress_percentage(self):
        """Calculate progress based on status"""
        status_progress = {
            'pending': 10,
            'paid': 25,
            'preparing': 60,
            'ready': 90,
            'completed': 100,
            'cancelled': 0
        }
        return status_progress.get(self.status, 0)
    
    def to_tracking_dict(self):
        """Convert order to dictionary for real-time tracking API"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'status': self.status,
            'progress': self.get_progress_percentage(),
            'elapsed_seconds': self.get_elapsed_time(),
            'estimated_ready_minutes': self.estimated_ready_minutes,
            'created_at': self.created_at.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'preparing_at': self.preparing_at.isoformat() if self.preparing_at else None,
            'ready_at': self.ready_at.isoformat() if self.ready_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'events': [event.to_dict() for event in self.tracking_events]
        }


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)


class OrderTracking(db.Model):
    """Tracks order status changes with timestamps for real-time tracking"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<OrderTracking {self.order_id}: {self.status}>'


class StaffClockIn(db.Model):
    """Tracks staff clock in/out times"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    clock_out = db.Column(db.DateTime, nullable=True)
    break_minutes = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(255))
    
    user = db.relationship('User', backref='clock_records')
    
    @property
    def is_active(self):
        return self.clock_out is None
    
    @property
    def hours_worked(self):
        end_time = self.clock_out or datetime.utcnow()
        delta = end_time - self.clock_in
        hours = delta.total_seconds() / 3600
        return round(hours - (self.break_minutes / 60), 2)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name or self.user.email,
            'clock_in': self.clock_in.isoformat(),
            'clock_out': self.clock_out.isoformat() if self.clock_out else None,
            'is_active': self.is_active,
            'hours_worked': self.hours_worked
        }


class DailySales(db.Model):
    """Daily sales summary for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    total_orders = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0)
    avg_order_value = db.Column(db.Float, default=0)
    top_item = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

