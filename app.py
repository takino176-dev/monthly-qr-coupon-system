import os
import io
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

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

class MonthlyRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month_period = db.Column(db.String(20), unique=True, nullable=False)
    working_days = db.Column(db.Integer, nullable=False, default=20)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), nullable=False)
    merchant_username = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    month_period = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password_hash=generate_password_hash('admin123'), role='admin'))
        db.session.commit()

# --- Routes ---
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
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    current_month = datetime.now().strftime("%Y-%m")
    current_rule = MonthlyRule.query.filter_by(month_period=current_month).first()
    if not current_rule:
        current_rule = MonthlyRule(month_period=current_month, working_days=20)

    return render_template('admin_dashboard.html',
                           emp_count=Employee.query.count(),
                           total_emp_balance=db.session.query(db.func.sum(Employee.balance)).scalar() or 0.0,
                           merchant_count=Merchant.query.count(),
                           spent_this_month=db.session.query(db.func.sum(Transaction.amount)).filter(Transaction.month_period == current_month).scalar() or 0.0,
                           current_rule=current_rule,
                           current_month=current_month,
                           users=User.query.all(),
                           employees=Employee.query.all())

@app.route('/admin/set-rule', methods=['POST'])
def set_rule():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    month_period = request.form.get('month_period', datetime.now().strftime("%Y-%m"))
    try:
        working_days = int(request.form.get('working_days', 20))
    except ValueError:
        working_days = 20
    
    rule = MonthlyRule.query.filter_by(month_period=month_period).first()
    if not rule:
        rule = MonthlyRule(month_period=month_period, working_days=working_days)
        db.session.add(rule)
    else:
        rule.working_days = working_days
    db.session.commit()
    flash('Working days updated successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload-employees', methods=['POST'])
def upload_employees():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please select an Excel file.', 'danger')
            return redirect(url_for('admin_dashboard'))

        current_month = datetime.now().strftime("%Y-%m")
        rule = MonthlyRule.query.filter_by(month_period=current_month).first()
        working_days = rule.working_days if rule else 20

        wb = openpyxl.load_workbook(io.BytesIO(file.read()))
        sheet = wb.active
        count = 0

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 5 or not row[4]:
                continue
            name = str(row[0]).strip() if row[0] else "Employee"
            sector = str(row[3]).strip() if len(row) > 3 and row[3] else "General"
            emp_id = str(row[4]).strip()
            excel_password = str(row[5]).strip() if len(row) > 5 and row[5] else "emp123"

            emp = Employee.query.filter_by(emp_id=emp_id).first()
            if not emp:
                emp = Employee(emp_id=emp_id, name=name, department=sector, qr_code_id=str(uuid.uuid4()), balance=float(working_days))
                db.session.add(emp)
            else:
                emp.balance += float(working_days)

            if not User.query.filter_by(username=emp_id).first():
                db.session.add(User(username=emp_id, password_hash=generate_password_hash(excel_password), role='employee'))
            
            count += 1

        db.session.commit()
        flash(f'Successfully imported {count} employees!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/monthly-closing/approve', methods=['POST'])
def approve_monthly_closing():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    for m in Merchant.query.all():
        m.collected_balance = 0.0
    for e in Employee.query.all():
        e.balance = 0.0
    db.session.commit()
    flash('Monthly closing reset successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)