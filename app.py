import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kolfe-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coupon_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'employee', 'merchant'
    is_initial_password = db.Column(db.Boolean, default=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    qr_code_id = db.Column(db.String(100), unique=True, nullable=False)  # Permanent QR Seed
    balance = db.Column(db.Float, default=0.0)

class Merchant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    collected_balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), nullable=False)
    merchant_username = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    month_period = db.Column(db.String(20), nullable=False)  # e.g. "2026-10"

class MonthlyRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month_period = db.Column(db.String(20), unique=True, nullable=False)
    working_days = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)

# ---------------------------------------------------------------------------
# Database Initialization & Admin Setup
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    # Ensure default Master Admin account exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        default_admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_initial_password=False
        )
        db.session.add(default_admin)
        db.session.commit()

# ---------------------------------------------------------------------------
# Routes & Controllers
# ---------------------------------------------------------------------------

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'merchant':
                return redirect(url_for('merchant_dashboard'))
            elif user.role == 'employee':
                return redirect(url_for('employee_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    emp_count = Employee.query.count()
    total_emp_balance = db.session.query(db.func.sum(Employee.balance)).scalar() or 0.0
    merchant_count = Merchant.query.count()

    current_month = datetime.now().strftime("%Y-%m")
    spent_this_month = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.month_period == current_month
    ).scalar() or 0.0

    users = User.query.all()

    return render_template('admin_dashboard.html