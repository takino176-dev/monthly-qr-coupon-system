import io
import os
import openpyxl
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this-in-production'

# SQLite Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) # e.g. Employee ID, 'admin', or Merchant Name
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee') # 'admin', 'employee', or 'merchant'
    is_initial_password = db.Column(db.Boolean, default=True)

# Create Database and Default Admin Account
def init_db():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Default Admin Password set to admin123 on first run
            hashed_pw = generate_password_hash('admin123') 
            new_admin = User(username='admin', password_hash=hashed_pw, role='admin', is_initial_password=False)
            db.session.add(new_admin)
            db.session.commit()

init_db()

# --- AUTHENTICATION & CORE ROUTES ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('upload_file'))
    elif role == 'merchant':
        return redirect(url_for('merchant_dashboard'))
    return redirect(url_for('user_dashboard'))

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
            
            # Force user to change initial/default password on first login
            if user.is_initial_password:
                flash('Please change your default password to continue.', 'warning')
                return redirect(url_for('change_password'))
                
            # Smart Role-Based Redirects
            if user.role == 'admin':
                return redirect(url_for('upload_file'))
            elif user.role == 'merchant':
                return redirect(url_for('merchant_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        
        user = User.query.get(session['user_id'])
        if check_password_hash(user.password_hash, old_password):
            user.password_hash = generate_password_hash(new_password)
            user.is_initial_password = False
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Current password is incorrect.', 'danger')
            
    return render_template('change_password.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARDS ---

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'employee':
        return redirect(url_for('login'))
    return render_template('user_dashboard.html', username=session['username'])

@app.route('/merchant')
def merchant_dashboard():
    if 'user_id' not in session or session.get('role') != 'merchant':
        return redirect(url_for('login'))
    return render_template('merchant_dashboard.html', username=session['username'])

# --- ADMIN MANAGEMENT & EXCEL UPLOAD ---

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            try:
                # Wrap file read into BytesIO for openpyxl
                file_stream = io.BytesIO(file.read())
                wb = openpyxl.load_workbook(file_stream)
                sheet = wb.active
                
                # Get headers from row 1 and normalize
                headers = [str(cell.value).strip().lower() for cell in sheet[1] if cell.value is not None]
                employees = []
                
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(row) and row[i] is not None:
                            row_dict[header] = str(row[i]).strip()
                        else:
                            row_dict[header] = ""
                    
                    if any(row_dict.values()):
                        employees.append(row_dict)
                        
                        # Automatically create user account if ID exists in sheet
                        emp_id_key = next((h for h in headers if 'id' in h), None)
                        if emp_id_key and row_dict.get(emp_id_key):
                            emp_username = row_dict[emp_id_key]
                            existing_user = User.query.filter_by(username=emp_username).first()
                            if not existing_user:
                                default_pw = generate_password_hash('welcome123') # Initial employee password
                                new_employee = User(
                                    username=emp_username,
                                    password_hash=default_pw,
                                    role='employee',
                                    is_initial_password=True
                                )
                                db.session.add(new_employee)
                
                db.session.commit()
                return render_template('print_coupons.html', employees=employees)
            except Exception as e:
                return f"Error reading file: {str(e)}.<br><br>Tip: Make sure your file is saved as an <b>Excel Workbook (*.xlsx)</b>.", 500
                
    return render_template('upload.html')

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    
    users = User.query.filter(User.role != 'admin').all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
def admin_reset_password(user_id):
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
        
    user = User.query.get(user_id)
    if user:
        # Reset user password to default temporary password
        user.password_hash = generate_password_hash('welcome123')
        user.is_initial_password = True
        db.session.commit()
        flash(f'Password for "{user.username}" has been reset to default (welcome123).', 'success')
    else:
        flash('User not found.', 'danger')
        
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(debug=True)