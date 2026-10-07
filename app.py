import os
import sqlite3
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'hardware_inventory.db')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'campus-hardware-inventory-2026')

import smtplib
import random
from email.mime.text import MIMEText

# --- BREVO SMTP CONFIGURATION ---
SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 2525
# TODO: Replace these with your actual Brevo SMTP Login and Master Password
SMTP_LOGIN = "your-email@example.com"       
SMTP_PASSWORD = "your-brevo-master-password"  

def send_otp_email(receiver_email, otp, intent):
    """Sends a 6-digit OTP using Brevo SMTP."""
    msg = MIMEText(f"Your {intent} One-Time Password (OTP) is: {otp}\n\nPlease enter this code to proceed. Do not share this code with anyone.")
    msg['Subject'] = f"Laboratory System - {intent} OTP"
    msg['From'] = "your-actual-email@gmail.com"  # Replace with your verified Brevo email
    msg['To'] = receiver_email
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def status_for(qty):
    if qty <= 0:
        return 'Out of Stock'
    if qty <= 9:
        return 'Low Stock'
    return 'In Stock'


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        if session.get('role') != 'ADMIN':
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard'))
        return fn(*args, **kwargs)
    return wrapper


def init_db():
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'USER',
        status TEXT NOT NULL DEFAULT 'ACTIVE'
    );

    CREATE TABLE IF NOT EXISTS hardware (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        unit_price REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS borrow_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        request_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        return_date TEXT
    );

    CREATE TABLE IF NOT EXISTS reset_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        request_date TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reset_password_data (
        request_id INTEGER PRIMARY KEY,
        password_hash TEXT NOT NULL
    );
    ''')

    # Repair databases created by older versions that did not enforce
    # unique hardware names. Repeated app starts could otherwise insert
    # the seed inventory again and again, making each item appear many times.
    duplicate_rows = conn.execute('''
        SELECT item_name, MIN(item_id) AS keep_id
        FROM hardware
        GROUP BY item_name
        HAVING COUNT(*) > 1
    ''').fetchall()
    for dup in duplicate_rows:
        duplicates = conn.execute(
            'SELECT item_id FROM hardware WHERE item_name=? AND item_id<>?',
            (dup['item_name'], dup['keep_id'])
        ).fetchall()
        for row in duplicates:
            # Keep existing borrow history attached to the retained item.
            conn.execute('UPDATE borrow_requests SET item_id=? WHERE item_id=?',
                         (dup['keep_id'], row['item_id']))
            conn.execute('DELETE FROM hardware WHERE item_id=?', (row['item_id'],))

    # Add a unique index so future startup/seed operations can never create
    # duplicate inventory rows, even when using an older database schema.
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_hardware_item_name ON hardware(item_name)')

    # Make sure the original Raspberry Pi Pico exists.
    seed = [
        ('Raspberry Pi Pico', 'Microcontroller', 10, 450),
        ('Arduino Uno R3', 'Microcontroller', 15, 450),
        ('Arduino Nano', 'Microcontroller', 15, 250),
        ('ESP32 Development Board', 'Microcontroller', 12, 350),
        ('ESP8266 NodeMCU', 'Microcontroller', 10, 280),
        ('Raspberry Pi 4 Model B', 'Single-board Computer', 5, 3200),
        ('HC-SR04 Ultrasonic Sensor', 'Sensor', 20, 85),
        ('DHT11 Temperature Sensor', 'Sensor', 20, 75),
        ('DHT22 Temperature Sensor', 'Sensor', 15, 180),
        ('PIR Motion Sensor', 'Sensor', 20, 65),
        ('IR Obstacle Sensor', 'Sensor', 20, 45),
        ('LDR Photoresistor Module', 'Sensor', 20, 35),
        ('MQ-2 Gas Sensor', 'Sensor', 10, 120),
        ('Servo Motor SG90', 'Motor', 15, 110),
        ('DC Gear Motor', 'Motor', 12, 95),
        ('L298N Motor Driver', 'Motor Driver', 10, 100),
        ('TB6612FNG Motor Driver', 'Motor Driver', 8, 220),
        ('0.96-inch OLED Display', 'Display', 12, 150),
        ('16x2 I2C LCD Display', 'Display', 12, 130),
        ('4-Digit 7-Segment Display', 'Display', 10, 90),
        ('74HC595 Shift Register', 'Integrated Circuit', 20, 35),
        ('7400 NAND Gate IC', 'Integrated Circuit', 20, 30),
        ('7483 4-bit Adder IC', 'Integrated Circuit', 12, 45),
        ('7486 XOR Gate IC', 'Integrated Circuit', 15, 40),
        ('Breadboard 830 Tie Points', 'Prototyping', 20, 120),
        ('Jumper Wire Kit', 'Prototyping', 25, 100),
        ('Resistor Kit', 'Electronic Components', 20, 150),
        ('LED Assorted Pack', 'Electronic Components', 25, 80),
        ('Tactile Push Button Pack', 'Electronic Components', 25, 60),
        ('10k Potentiometer', 'Electronic Components', 20, 25),
        ('Multimeter', 'Test Equipment', 6, 450),
        ('Soldering Iron', 'Tools', 5, 350),
        ('USB Type-C Cable', 'Accessories', 15, 100),
        ('nRF24L01 Wireless Module', 'Communication', 10, 200),
        ('HC-05 Bluetooth Module', 'Communication', 8, 180),
    ]
    for name, category, qty, price in seed:
        conn.execute('''INSERT OR IGNORE INTO hardware
            (item_name, category, quantity, unit_price, status)
            VALUES (?, ?, ?, ?, ?)''', (name, category, qty, price, status_for(qty)))

    # Always make sure the built-in administrator can log in.
    # This also repairs an existing database whose admin password was
    # created by an older version of the project.
    admin = conn.execute('SELECT user_id FROM users WHERE username=?', ('admin',)).fetchone()
    admin_hash = generate_password_hash('Admin@123')
    if not admin:
        conn.execute('''INSERT INTO users(username,email,password,role,status)
                        VALUES(?,?,?,?,?)''',
                     ('admin', 'admin@campus.local', admin_hash, 'ADMIN', 'ACTIVE'))
    else:
        conn.execute('''UPDATE users
                        SET email=?, password=?, role='ADMIN', status='ACTIVE'
                        WHERE username='admin' ''',
                     ('admin@campus.local', admin_hash))
    conn.commit()
    conn.close()


@app.context_processor
def inject_globals():
    return {'today': date.today().strftime('%b %d, %Y')}


@app.route('/')
def index():
    return redirect(url_for('dashboard')) if session.get('user_id') else redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = db()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        if not user or user['status'] != 'ACTIVE' or not check_password_hash(user['password'], password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
        session.clear()
        session.update(user_id=user['user_id'], username=user['username'], email=user['email'], role=user['role'])
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'warning')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            conn = db()
            try:
                conn.execute('INSERT INTO users(username,email,password) VALUES(?,?,?)',
                             (username, email, generate_password_hash(password)))
                conn.commit()
                flash('Account created. You can now log in.', 'success')
                conn.close()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                conn.close()
                flash('Username or email already exists.', 'danger')
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = db()
    total_stocks = conn.execute('SELECT COALESCE(SUM(quantity),0) n FROM hardware').fetchone()['n']
    total_items = conn.execute('SELECT COUNT(*) n FROM hardware').fetchone()['n']
    borrowed_items = conn.execute("SELECT COALESCE(SUM(quantity),0) n FROM borrow_requests WHERE status='BORROWED'").fetchone()['n']
    pending_borrows = conn.execute("SELECT COUNT(*) n FROM borrow_requests WHERE status='PENDING'").fetchone()['n']
    pending_returns = conn.execute("SELECT COUNT(*) n FROM borrow_requests WHERE status='RETURN_PENDING'").fetchone()['n']
    password_requests = conn.execute("SELECT COUNT(*) n FROM reset_requests WHERE status='PENDING'").fetchone()['n']
    low_stock = conn.execute("SELECT COUNT(*) n FROM hardware WHERE quantity BETWEEN 1 AND 9").fetchone()['n']
    out_stock = conn.execute("SELECT COUNT(*) n FROM hardware WHERE quantity <= 0").fetchone()['n']
    recent = conn.execute('''SELECT b.*, h.item_name FROM borrow_requests b
                             JOIN hardware h ON h.item_id=b.item_id
                             ORDER BY b.request_id DESC LIMIT 6''').fetchall()
    conn.close()
    return render_template('dashboard.html', total_stocks=total_stocks, total_items=total_items,
                           borrowed_items=borrowed_items, pending_borrows=pending_borrows,
                           pending_returns=pending_returns, password_requests=password_requests,
                           low_stock=low_stock, out_stock=out_stock, recent=recent)


@app.route('/inventory')
@login_required
def inventory():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    conn = db()
    sql = 'SELECT * FROM hardware WHERE 1=1'
    params = []
    if search:
        sql += ' AND item_name LIKE ?'
        params.append(f'%{search}%')
    if category:
        sql += ' AND category=?'
        params.append(category)
    sql += ' ORDER BY item_name'
    items = conn.execute(sql, params).fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM hardware ORDER BY category').fetchall()
    total = conn.execute('SELECT COUNT(*) n FROM hardware').fetchone()['n']
    in_stock = conn.execute("SELECT COUNT(*) n FROM hardware WHERE quantity >= 10").fetchone()['n']
    low = conn.execute("SELECT COUNT(*) n FROM hardware WHERE quantity BETWEEN 1 AND 9").fetchone()['n']
    out = conn.execute("SELECT COUNT(*) n FROM hardware WHERE quantity <= 0").fetchone()['n']
    conn.close()
    return render_template('inventory.html', inventory=items, categories=categories, search=search,
                           category=category, total=total, in_stock=in_stock, low=low, out=out)


@app.route('/inventory/add', methods=['GET', 'POST'])
@admin_required
def add_inventory():
    if request.method == 'POST':
        name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        qty = int(request.form.get('quantity', 0))
        price = float(request.form.get('unit_price', 0))
        conn = db()
        try:
            conn.execute('INSERT INTO hardware(item_name,category,quantity,unit_price,status) VALUES(?,?,?,?,?)',
                         (name, category, qty, price, status_for(qty)))
            conn.commit()
            flash('Inventory item added.', 'success')
        except sqlite3.IntegrityError:
            flash('That item already exists.', 'danger')
        conn.close()
        return redirect(url_for('inventory'))
    return render_template('add_inventory.html')


@app.route('/inventory/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_inventory(item_id):
    conn = db()
    item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (item_id,)).fetchone()
    if not item:
        conn.close(); flash('Item not found.', 'danger'); return redirect(url_for('inventory'))
    if request.method == 'POST':
        name = request.form.get('item_name', '').strip()
        category = request.form.get('category', '').strip()
        qty = int(request.form.get('quantity', 0))
        price = float(request.form.get('unit_price', 0))
        conn.execute('''UPDATE hardware SET item_name=?,category=?,quantity=?,unit_price=?,status=? WHERE item_id=?''',
                     (name, category, qty, price, status_for(qty), item_id))
        conn.commit(); conn.close()
        flash('Inventory updated.', 'success')
        return redirect(url_for('inventory'))
    conn.close()
    return render_template('edit_inventory.html', item=item)


@app.post('/inventory/delete/<int:item_id>')
@admin_required
def delete_inventory(item_id):
    conn = db(); conn.execute('DELETE FROM hardware WHERE item_id=?', (item_id,)); conn.commit(); conn.close()
    flash('Inventory item deleted.', 'success')
    return redirect(url_for('inventory'))


@app.route('/borrow/<int:item_id>', methods=['GET', 'POST'])
@login_required
def borrow_item(item_id):
    conn = db(); item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (item_id,)).fetchone()
    if not item:
        conn.close(); flash('Item not found.', 'danger'); return redirect(url_for('inventory'))
    if request.method == 'POST':
        qty = int(request.form.get('quantity', 0)); due = request.form.get('due_date', '')
        if qty < 1 or qty > item['quantity']:
            flash('Requested quantity is not available.', 'danger')
        elif not due:
            flash('Please select a due date.', 'warning')
        else:
            conn.execute('''INSERT INTO borrow_requests(item_id,username,quantity,request_date,due_date,status)
                            VALUES(?,?,?,?,?,'PENDING')''',
                         (item_id, session['username'], qty, date.today().isoformat(), due))
            conn.commit(); conn.close(); flash('Borrow request submitted.', 'success'); return redirect(url_for('inventory'))
    conn.close(); return render_template('borrow.html', item=item)


@app.route('/my-borrows')
@login_required
def my_borrows():
    conn = db(); rows = conn.execute('''SELECT b.*,h.item_name FROM borrow_requests b JOIN hardware h ON h.item_id=b.item_id
                                         WHERE b.username=? ORDER BY b.request_id DESC''', (session['username'],)).fetchall(); conn.close()
    return render_template('my_borrows.html', requests=rows)


@app.post('/return/<int:request_id>')
@login_required
def request_return(request_id):
    conn = db(); row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND username=?', (request_id, session['username'])).fetchone()
    if row and row['status'] == 'BORROWED':
        conn.execute("UPDATE borrow_requests SET status='RETURN_PENDING' WHERE request_id=?", (request_id,)); conn.commit(); flash('Return request submitted.', 'success')
    else:
        flash('This item cannot be returned right now.', 'warning')
    conn.close(); return redirect(url_for('my_borrows'))


@app.route('/approvals')
@admin_required
def admin_approvals():
    conn = db()
    borrows = conn.execute('''SELECT b.*,h.item_name FROM borrow_requests b JOIN hardware h ON h.item_id=b.item_id
                              WHERE b.status='PENDING' ORDER BY b.request_id DESC''').fetchall()
    returns = conn.execute('''SELECT b.*,h.item_name FROM borrow_requests b JOIN hardware h ON h.item_id=b.item_id
                              WHERE b.status='RETURN_PENDING' ORDER BY b.request_id DESC''').fetchall()
    resets = conn.execute("SELECT * FROM reset_requests WHERE status='PENDING' ORDER BY request_id DESC").fetchall()
    conn.close()
    return render_template('admin_approvals.html', borrow_requests=borrows, return_requests=returns, reset_requests=resets)


@app.post('/approvals/borrow/<int:request_id>/approve')
@admin_required
def approve_borrow(request_id):
    conn = db(); row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND status="PENDING"', (request_id,)).fetchone()
    if row:
        item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (row['item_id'],)).fetchone()
        if item and item['quantity'] >= row['quantity']:
            new_qty = item['quantity'] - row['quantity']
            conn.execute('UPDATE hardware SET quantity=?,status=? WHERE item_id=?', (new_qty, status_for(new_qty), item['item_id']))
            conn.execute("UPDATE borrow_requests SET status='BORROWED' WHERE request_id=?", (request_id,)); conn.commit(); flash('Borrow request approved.', 'success')
        else: flash('Not enough stock to approve this request.', 'danger')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/borrow/<int:request_id>/reject')
@admin_required
def reject_borrow(request_id):
    conn = db(); conn.execute("UPDATE borrow_requests SET status='REJECTED' WHERE request_id=? AND status='PENDING'", (request_id,)); conn.commit(); conn.close(); flash('Borrow request rejected.', 'success'); return redirect(url_for('admin_approvals'))


@app.post('/approvals/return/<int:request_id>/approve')
@admin_required
def approve_return(request_id):
    conn = db(); row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND status="RETURN_PENDING"', (request_id,)).fetchone()
    if row:
        item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (row['item_id'],)).fetchone()
        new_qty = item['quantity'] + row['quantity']
        conn.execute('UPDATE hardware SET quantity=?,status=? WHERE item_id=?', (new_qty, status_for(new_qty), item['item_id']))
        conn.execute("UPDATE borrow_requests SET status='RETURNED',return_date=? WHERE request_id=?", (date.today().isoformat(), request_id)); conn.commit(); flash('Return approved and stock restored.', 'success')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/return/<int:request_id>/reject')
@admin_required
def reject_return(request_id):
    conn = db(); conn.execute("UPDATE borrow_requests SET status='BORROWED' WHERE request_id=? AND status='RETURN_PENDING'", (request_id,)); conn.commit(); conn.close(); flash('Return request rejected.', 'success'); return redirect(url_for('admin_approvals'))


@app.route('/reset-request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        username = request.form.get('username', '').strip(); email = request.form.get('email', '').strip(); new_password = request.form.get('new_password', '')
        if len(new_password) < 8:
            flash('New password must contain at least 8 characters.', 'warning')
            return render_template('reset.html')
        conn = db(); user = conn.execute('SELECT * FROM users WHERE username=? AND email=?', (username, email)).fetchone()
        if not user:
            conn.close(); flash('No matching account was found.', 'danger'); return render_template('reset.html')
        existing = conn.execute("SELECT request_id FROM reset_requests WHERE username=? AND status='PENDING'", (username,)).fetchone()
        if existing:
            conn.close(); flash('You already have a pending password request.', 'warning'); return render_template('reset.html')
        cur = conn.execute('''INSERT INTO reset_requests(username,email,status,request_date) VALUES(?,?, 'PENDING', ?)''', (username,email,date.today().isoformat()))
        request_id = cur.lastrowid
        conn.execute('INSERT INTO reset_password_data(request_id,password_hash) VALUES(?,?)', (request_id, generate_password_hash(new_password)))
        conn.commit(); conn.close(); flash('Password request sent for administrator approval.', 'success'); return redirect(url_for('login'))
    return render_template('reset.html')


@app.post('/approvals/password/<int:request_id>/approve')
@admin_required
def approve_reset(request_id):
    conn = db(); req = conn.execute("SELECT * FROM reset_requests WHERE request_id=? AND status='PENDING'", (request_id,)).fetchone(); pw = conn.execute('SELECT * FROM reset_password_data WHERE request_id=?', (request_id,)).fetchone()
    if req and pw:
        conn.execute('UPDATE users SET password=? WHERE username=? AND email=?', (pw['password_hash'], req['username'], req['email']))
        conn.execute("UPDATE reset_requests SET status='APPROVED' WHERE request_id=?", (request_id,)); conn.execute('DELETE FROM reset_password_data WHERE request_id=?', (request_id,)); conn.commit(); flash('Password request approved.', 'success')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/password/<int:request_id>/reject')
@admin_required
def reject_reset(request_id):
    conn = db(); conn.execute("UPDATE reset_requests SET status='REJECTED' WHERE request_id=? AND status='PENDING'", (request_id,)); conn.execute('DELETE FROM reset_password_data WHERE request_id=?', (request_id,)); conn.commit(); conn.close(); flash('Password request rejected.', 'success'); return redirect(url_for('admin_approvals'))


# Initialize/repair the database whenever the application is imported or started.
# This makes both `python app.py` and Flask's development server work correctly.
init_db()

if __name__ == '__main__':
    app.run(debug=True)
