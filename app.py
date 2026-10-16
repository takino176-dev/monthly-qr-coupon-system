import base64
import csv
import io
from datetime import datetime, timezone

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
import qrcode
from werkzeug.security import check_password_hash, generate_password_hash

# Initialize Flask Application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr_coupon.db'

# Initialize Database Instance
db = SQLAlchemy(app)

# Define Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin', 'merchant', 'employee'
    full_name = db.Column(db.String(150), nullable=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=True)

class CouponAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False)
    month = db.Column(db.String(20), nullable=False)  # e.g., 'October 2026'
    allocated_amount = db.Column(db.Integer, nullable=False)
    current_balance = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'Released', 'Pending'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False)
    merchant_username = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Create Tables and Default Admin User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('ChangeMeAdmin123!', method='pbkdf2:sha256')
        admin_user = User(
            username='admin',
            password=hashed_password,
            role='admin',
            full_name='System Administrator'
        )
        db.session.add(admin_user)
        db.session.commit()

# Define Application Routes
@app.route('/')
def index():
    if 'username' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'merchant':
            return redirect(url_for('merchant_dashboard'))
        elif session['role'] == 'employee':
            return redirect(url_for('employee_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['role'] = user.role
            session['employee_id'] = user.employee_id
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'create_user' in request.form:
            username = request.form['username']
            password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
            role = request.form['role']
            full_name = request.form['full_name']
            employee_id = request.form.get('employee_id') if role == 'employee' else None
            
            new_user = User(
                username=username,
                password=password,
                role=role,
                full_name=full_name,
                employee_id=employee_id
            )
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully!', 'success')
            
        elif 'allocate_coupon' in request.form:
            emp_id = request.form['employee_id']
            month = request.form['month']
            amount = int(request.form['amount'])
            
            allocation = CouponAllocation(
                employee_id=emp_id,
                month=month,
                allocated_amount=amount,
                current_balance=amount,
                status='Released'
            )
            db.session.add(allocation)
            db.session.commit()
            flash('Coupons allocated successfully!', 'success')

    users = User.query.all()
    allocations = CouponAllocation.query.all()
    return render_template('admin.html', users=users, allocations=allocations)

@app.route('/employee')
def employee_dashboard():
    if 'username' not in session or session['role'] != 'employee':
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    allocations = CouponAllocation.query.filter_by(employee_id=user.employee_id).all()
    transactions = Transaction.query.filter_by(employee_id=user.employee_id).all()
    
    # Generate QR Code for employee ID
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(user.employee_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return render_template(
        'employee.html',
        user=user,
        allocations=allocations,
        transactions=transactions,
        qr_base64=qr_base64
    )

@app.route('/merchant', methods=['GET', 'POST'])
def merchant_dashboard():
    if 'username' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))
    
    current_month = datetime.now().strftime('%B %Y')
    
    if request.method == 'POST':
        employee_id = request.form['employee_id'].strip()
        amount = int(request.form['amount'])
        
        # Find any active allocation for this employee with enough balance
        allocation = CouponAllocation.query.filter_by(
            employee_id=employee_id,
            status='Released'
        ).filter(CouponAllocation.current_balance >= amount).first()
        
        if allocation:
            allocation.current_balance -= amount
            tx = Transaction(
                employee_id=employee_id,
                merchant_username=session['username'],
                amount=amount
            )
            db.session.add(tx)
            db.session.commit()
            flash(f'Successfully deducted {amount} coupon(s) for {employee_id}!', 'success')
        else:
            flash('Insufficient coupon balance or invalid employee ID!', 'danger')
            
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(10).all()
    return render_template('merchant.html', transactions=transactions, current_month=current_month)

@app.route('/admin/export_csv')
def export_csv():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    
    def generate():
        data = [['Transaction ID', 'Employee ID', 'Merchant Username', 'Amount', 'Timestamp']]
        yield ','.join(data[0]) + '\n'
        for tx in transactions:
            row = [
                str(tx.id),
                str(tx.employee_id),
                str(tx.merchant_username),
                str(tx.amount),
                tx.timestamp.strftime('%Y-%m-%d %H:%M:%S') if tx.timestamp else ''
            ]
            yield ','.join(row) + '\n'

    return Response(
        generate(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=coupon_transactions.csv'}
    )

# Run Application
if __name__ == '__main__':
    app.run(debug=True)