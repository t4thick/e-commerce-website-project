from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Order

manager_bp = Blueprint('manager', __name__)


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            flash('You need staff access to view this page.', 'error')
            return redirect(url_for('auth.staff_portal'))
        return f(*args, **kwargs)
    return decorated_function


@manager_bp.route('/manager')
@login_required
@staff_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()

    stats = {
        'total_orders': Order.query.count(),
        'pending': Order.query.filter(Order.status.in_(['pending', 'paid'])).count(),
        'preparing': Order.query.filter_by(status='preparing').count(),
        'ready': Order.query.filter_by(status='ready').count(),
        'revenue': db.session.query(db.func.sum(Order.total)).filter(
            Order.status != 'cancelled'
        ).scalar() or 0
    }

    return render_template('manager.html', orders=orders, stats=stats)


@manager_bp.route('/manager/order/<int:order_id>/status', methods=['POST'])
@login_required
@staff_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    valid_statuses = ['pending', 'paid', 'preparing', 'ready', 'completed', 'cancelled']
    if new_status in valid_statuses:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.order_number} updated to {new_status}.', 'success')

    return redirect(url_for('manager.dashboard'))

