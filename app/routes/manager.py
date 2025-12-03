import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from app import db
from app.models import Order, User, MenuItem, StaffClockIn, OrderItem

logger = logging.getLogger(__name__)

manager_bp = Blueprint('manager', __name__)


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            flash('You need staff access to view this page.', 'error')
            return redirect(url_for('auth.staff_portal'))
        return f(*args, **kwargs)
    return decorated_function


def get_analytics():
    """Calculate comprehensive analytics"""
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's stats
    today_orders = Order.query.filter(
        func.date(Order.created_at) == today,
        Order.status != 'cancelled'
    ).all()
    today_revenue = sum(o.total for o in today_orders)
    
    # This week's stats
    week_orders = Order.query.filter(
        func.date(Order.created_at) >= week_ago,
        Order.status != 'cancelled'
    ).all()
    week_revenue = sum(o.total for o in week_orders)
    
    # This month's stats
    month_orders = Order.query.filter(
        func.date(Order.created_at) >= month_ago,
        Order.status != 'cancelled'
    ).all()
    month_revenue = sum(o.total for o in month_orders)
    
    # Average order value
    avg_order = month_revenue / len(month_orders) if month_orders else 0
    
    # Top selling items (last 30 days)
    top_items = db.session.query(
        OrderItem.name,
        func.sum(OrderItem.quantity).label('total_qty')
    ).join(Order).filter(
        func.date(Order.created_at) >= month_ago,
        Order.status != 'cancelled'
    ).group_by(OrderItem.name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    # Hourly distribution for today
    hourly_orders = {}
    for order in today_orders:
        hour = order.created_at.hour
        hourly_orders[hour] = hourly_orders.get(hour, 0) + 1
    
    # Daily revenue for the past 7 days
    daily_revenue = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_orders = Order.query.filter(
            func.date(Order.created_at) == day,
            Order.status != 'cancelled'
        ).all()
        daily_revenue.append({
            'date': day.strftime('%a'),
            'revenue': sum(o.total for o in day_orders),
            'orders': len(day_orders)
        })
    
    return {
        'today_orders': len(today_orders),
        'today_revenue': today_revenue,
        'week_orders': len(week_orders),
        'week_revenue': week_revenue,
        'month_orders': len(month_orders),
        'month_revenue': month_revenue,
        'avg_order_value': avg_order,
        'top_items': top_items,
        'hourly_orders': hourly_orders,
        'daily_revenue': daily_revenue
    }


@manager_bp.route('/manager')
@login_required
@staff_required
def dashboard():
    logger.info(f'Dashboard accessed by {current_user.email}')
    
    # Get orders
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    active_orders = [o for o in orders if o.status in ['paid', 'preparing', 'ready']]
    
    # Basic stats
    stats = {
        'total_orders': Order.query.count(),
        'pending': Order.query.filter(Order.status.in_(['pending', 'paid'])).count(),
        'preparing': Order.query.filter_by(status='preparing').count(),
        'ready': Order.query.filter_by(status='ready').count(),
        'completed_today': Order.query.filter(
            Order.status == 'completed',
            func.date(Order.created_at) == datetime.utcnow().date()
        ).count(),
        'revenue': db.session.query(func.sum(Order.total)).filter(
            Order.status != 'cancelled'
        ).scalar() or 0
    }
    
    # Analytics
    analytics = get_analytics()
    
    # Staff currently clocked in
    active_staff = StaffClockIn.query.filter_by(clock_out=None).all()
    
    # All staff members
    all_staff = User.query.filter(User.role.in_(['staff', 'manager', 'admin'])).all()
    
    # Current user's clock status
    my_clock = StaffClockIn.query.filter_by(
        user_id=current_user.id,
        clock_out=None
    ).first()
    
    # Today's clock records
    today_clocks = StaffClockIn.query.filter(
        func.date(StaffClockIn.clock_in) == datetime.utcnow().date()
    ).order_by(StaffClockIn.clock_in.desc()).all()
    
    return render_template('manager.html', 
        orders=orders,
        active_orders=active_orders,
        stats=stats,
        analytics=analytics,
        active_staff=active_staff,
        all_staff=all_staff,
        my_clock=my_clock,
        today_clocks=today_clocks,
        now=datetime.utcnow()
    )


@manager_bp.route('/manager/order/<int:order_id>/status', methods=['POST'])
@login_required
@staff_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')

    valid_statuses = ['pending', 'paid', 'preparing', 'ready', 'completed', 'cancelled']
    if new_status in valid_statuses:
        order.update_status(new_status, notes=notes or f'Updated by {current_user.name or current_user.email}')
        db.session.commit()
        
        logger.info(f'Order {order.order_number} status updated to {new_status} by {current_user.email}')
        flash(f'Order #{order.order_number} updated to {new_status}.', 'success')
    else:
        logger.warning(f'Invalid status {new_status} attempted for order {order.order_number}')

    return redirect(url_for('manager.dashboard'))


# ============ CLOCK IN/OUT ============

@manager_bp.route('/manager/clock-in', methods=['POST'])
@login_required
@staff_required
def clock_in():
    # Check if already clocked in
    existing = StaffClockIn.query.filter_by(
        user_id=current_user.id,
        clock_out=None
    ).first()
    
    if existing:
        flash('You are already clocked in!', 'error')
        return redirect(url_for('manager.dashboard'))
    
    clock_record = StaffClockIn(
        user_id=current_user.id,
        clock_in=datetime.utcnow(),
        notes=request.form.get('notes', '')
    )
    db.session.add(clock_record)
    db.session.commit()
    
    logger.info(f'{current_user.email} clocked in at {clock_record.clock_in}')
    flash('Successfully clocked in! 🟢', 'success')
    return redirect(url_for('manager.dashboard'))


@manager_bp.route('/manager/clock-out', methods=['POST'])
@login_required
@staff_required
def clock_out():
    clock_record = StaffClockIn.query.filter_by(
        user_id=current_user.id,
        clock_out=None
    ).first()
    
    if not clock_record:
        flash('You are not clocked in!', 'error')
        return redirect(url_for('manager.dashboard'))
    
    clock_record.clock_out = datetime.utcnow()
    clock_record.break_minutes = int(request.form.get('break_minutes', 0))
    db.session.commit()
    
    logger.info(f'{current_user.email} clocked out. Worked {clock_record.hours_worked} hours')
    flash(f'Clocked out! You worked {clock_record.hours_worked} hours today. 🔴', 'success')
    return redirect(url_for('manager.dashboard'))


@manager_bp.route('/manager/api/stats')
@login_required
@staff_required
def api_stats():
    """API endpoint for real-time dashboard updates"""
    stats = {
        'pending': Order.query.filter(Order.status.in_(['pending', 'paid'])).count(),
        'preparing': Order.query.filter_by(status='preparing').count(),
        'ready': Order.query.filter_by(status='ready').count(),
        'active_staff': StaffClockIn.query.filter_by(clock_out=None).count()
    }
    return jsonify(stats)


@manager_bp.route('/manager/api/orders')
@login_required
@staff_required
def api_orders():
    """API endpoint for real-time order updates"""
    orders = Order.query.filter(
        Order.status.in_(['paid', 'preparing', 'ready'])
    ).order_by(Order.created_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': o.id,
        'order_number': o.order_number,
        'customer_name': o.customer_name,
        'status': o.status,
        'total': o.total,
        'items': [{'name': i.name, 'qty': i.quantity} for i in o.items],
        'created_at': o.created_at.isoformat(),
        'elapsed_minutes': int((datetime.utcnow() - o.created_at).total_seconds() / 60)
    } for o in orders])
