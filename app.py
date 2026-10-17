# --- MONTHLY COUPON DISTRIBUTION ROUTES ---

@app.route('/admin/release-coupon/single', methods=['POST'])
def release_single_coupon():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
        
    emp_id = request.form.get('emp_id', '').strip()
    emp_name = request.form.get('emp_name', '').strip() or emp_id
    department = request.form.get('department', '').strip() or 'N/A'
    
    if not emp_id:
        flash('Employee ID is required.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    # Auto-create user account if it doesn't exist yet
    existing_user = User.query.filter_by(username=emp_id).first()
    if not existing_user:
        default_pw = generate_password_hash('welcome123')
        new_employee = User(
            username=emp_id,
            password_hash=default_pw,
            role='employee',
            is_initial_password=True
        )
        db.session.add(new_employee)
        db.session.commit()
        
    # Format single employee dictionary for coupon rendering
    single_employee = [{
        'id': emp_id,
        'name': emp_name,
        'department': department
    }]
    
    flash(f'Monthly coupon released for Employee ID: {emp_id}', 'success')
    return render_template('print_coupons.html', employees=single_employee)