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

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'employee', 'merchant'
    is_initial_password = db.Column(db.Boolean, default=True)
    
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    qr_code_id = db.Column(db.String(100), unique=True, nullable=False) # Permanent QR Seed
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
    month_period = db.Column(db.String(20), nullable=False) # e.g. "2026-10"

class MonthlyRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month_period = db.Column(db.String(20), unique=True, nullable=False)
    working_days = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)

# Routes & Logic

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
    
    return render_template('admin_dashboard.html', 
                           emp_count=emp_count,
                           total_emp_balance=total_emp_balance,
                           merchant_count=merchant_count,
                           spent_this_month=spent_this_month,
                           users=users)

@app.route('/admin/add-merchant', methods=['POST'])
def add_merchant():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    # Enforce strict 1-merchant rule
    if Merchant.query.count() >= 1:
        flash('System constraint: Only 1 primary merchant account is permitted.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    username = request.form.get('username').strip()
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))
        
    new_user = User(username=username, password_hash=generate_password_hash('welcome123'), role='merchant')
    new_merchant = Merchant(username=username)
    
    db.session.add(new_user)
    db.session.add(new_merchant)
    db.session.commit()
    
    flash(f'Merchant account "{username}" created successfully with default password welcome123.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/merchant/charge', methods=['POST'])
def merchant_charge():
    if session.get('role') != 'merchant':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.json
    emp_id = data.get('emp_id')
    amount = float(data.get('amount', 0))
    
    employee = Employee.query.filter_by(emp_id=emp_id).first()
    merchant = Merchant.query.filter_by(username=session.get('username')).first()
    
    if not employee:
        return jsonify({'success': False, 'message': 'Employee QR Code not found.'}), 404
        
    if employee.balance < amount:
        return jsonify({'success': False, 'message': f'Insufficient balance! Available: {employee.balance}'}), 400
        
    try:
        # Atomic Transaction Update
        employee.balance -= amount
        merchant.collected_balance += amount
        
        current_month = datetime.now().strftime("%Y-%m")
        txn = Transaction(emp_id=employee.emp_id, merchant_username=merchant.username, amount=amount, month_period=current_month)
        
        db.session.add(txn)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Charged {amount} successfully. Remaining employee balance: {employee.balance}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Transaction failed due to database error.'}), 500

@app.route('/admin/monthly-closing/approve', methods=['POST'])
def approve_monthly_closing():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    try:
        # 1. Reset Merchant Balances to 0 (Keep transaction logs intact)
        merchants = Merchant.query.all()
        for m in merchants:
            m.collected_balance = 0.0
            
        # 2. Expire remaining employee balances
        employees = Employee.query.all()
        for e in employees:
            e.balance = 0.0
            
        db.session.commit()
        flash('Monthly closing approved successfully. Merchant and employee balances reset to 0.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to approve monthly closing.', 'danger')
        
    return redirect(url_for('admin_dashboard'))