import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl
from datetime import datetime
import uuid

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

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    qr_code_id = db.Column(db.String(100), unique=True, nullable=False)
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
    month_period = db.Column(db.String(20), nullable=False)

# ---------------------------------------------------------------------------
# Database Initialization & Admin Setup
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        default_admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
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
    employees = Employee.query.all()

    return render_template('admin_dashboard.html',
                           emp_count=emp_count,
                           total_emp_balance=total_emp_balance,
                           merchant_count=merchant_count,
                           spent_this_month=spent_this_month,
                           users=users,
                           employees=employees)

@app.route('/admin/add-merchant', methods=['POST'])
def add_merchant():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    if Merchant.query.count() >= 1:
        flash('System constraint: Only 1 primary merchant account is permitted.', 'danger')
        return redirect(url_for('admin_dashboard'))

    username = request.form.get('username', '').strip()
    if not username:
        flash('Merchant username cannot be empty.', 'warning')
        return redirect(url_for('admin_dashboard'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))

    new_user = User(
        username=username,
        password_hash=generate_password_hash('welcome123'),
        role='merchant'
    )
    new_merchant = Merchant(username=username)

    db.session.add(new_user)
    db.session.add(new_merchant)
    db.session.commit()

    flash(f'Merchant account "{username}" created successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload-employees', methods=['POST'])
def upload_employees():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    file = request.files.get('file')
    if not file or not file.filename.endswith('.xlsx'):
        flash('Please upload a valid Excel (.xlsx) file.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        wb = openpyxl.load_workbook(file)
        sheet = wb.active
        count = 0
        
        # Assumes format: Emp ID | Name | Department | Monthly Allocation Amount
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            emp_id = str(row[0]).strip()
            name = str(row[1]) if len(row) > 1 and row[1] else "Employee"
            dept = str(row[2]) if len(row) > 2 and row[2] else "General"
            allocation = float(row[3]) if len(row) > 3 and row[3] else 1000.0

            emp = Employee.query.filter_by(emp_id=emp_id).first()
            if not emp:
                qr_seed = str(uuid.uuid4())
                emp = Employee(emp_id=emp_id, name=name, department=dept, qr_code_id=qr_seed, balance=allocation)
                db.session.add(emp)
                
                # Create user login for employee
                if not User.query.filter_by(username=emp_id).first():
                    u = User(username=emp_id, password_hash=generate_password_hash('emp123'), role='employee')
                    db.session.add(u)
            else:
                emp.balance += allocation

            count += 1

        db.session.commit()
        flash(f'Successfully processed {count} employee allocations from Excel!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing Excel file: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/release-single', methods=['POST'])
def release_single():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    emp_id = request.form.get('emp_id', '').strip()
    name = request.form.get('name', '').strip()
    amount = float(request.form.get('amount', 500.0))

    if not emp_id:
        flash('Employee ID is required.', 'warning')
        return redirect(url_for('admin_dashboard'))

    emp = Employee.query.filter_by(emp_id=emp_id).first()
    if not emp:
        qr_seed = str(uuid.uuid4())
        emp = Employee(emp_id=emp_id, name=name or 'Employee', qr_code_id=qr_seed, balance=amount)
        db.session.add(emp)
        
        if not User.query.filter_by(username=emp_id).first():
            u = User(username=emp_id, password_hash=generate_password_hash('emp123'), role='employee')
            db.session.add(u)
    else:
        emp.balance += amount

    db.session.commit()
    flash(f'Released {amount} coupon balance to employee {emp_id} successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/monthly-closing/approve', methods=['POST'])
def approve_monthly_closing():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        for m in Merchant.query.all():
            m.collected_balance = 0.0
        for e in Employee.query.all():
            e.balance = 0.0

        db.session.commit()
        flash('Monthly closing approved successfully. All balances reset to 0.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to execute monthly closing.', 'danger')

    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)