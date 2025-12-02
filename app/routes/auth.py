from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import random
import string
from app import db
from app.models import User, StaffCode, OTPToken

auth_bp = Blueprint('auth', __name__)


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            otp = generate_otp()
            expires = datetime.utcnow() + timedelta(minutes=10)

            OTPToken.query.filter_by(user_id=user.id).delete()

            token = OTPToken(user_id=user.id, token=otp, expires_at=expires)
            db.session.add(token)
            db.session.commit()

            session['pending_user_id'] = user.id
            session['dev_otp'] = otp

            return redirect(url_for('auth.verify_otp'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    dev_otp = session.get('dev_otp')

    if request.method == 'POST':
        otp = request.form.get('otp')

        token = OTPToken.query.filter_by(user_id=user_id, token=otp).first()

        if token and token.expires_at > datetime.utcnow():
            user = User.query.get(user_id)
            login_user(user)

            OTPToken.query.filter_by(user_id=user_id).delete()
            db.session.commit()

            session.pop('pending_user_id', None)
            session.pop('dev_otp', None)

            flash(f'Welcome back, {user.name or user.email}!', 'success')

            if user.is_staff():
                return redirect(url_for('manager.dashboard'))
            return redirect(url_for('main.home'))

        flash('Invalid or expired OTP code.', 'error')

    return render_template('verify_otp.html', dev_otp=dev_otp)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

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
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))


@auth_bp.route('/staff-portal', methods=['GET', 'POST'])
@login_required
def staff_portal():
    if current_user.is_staff():
        return redirect(url_for('manager.dashboard'))

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
            return redirect(url_for('manager.dashboard'))

    return render_template('staff_portal.html')

