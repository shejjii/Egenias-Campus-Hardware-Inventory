import os
import sqlite3
import smtplib
import random
from datetime import date
from functools import wraps
from email.mime.text import MIMEText

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DATABASE = os.path.join(BASE_DIR, 'hardware_inventory.db')
DATABASE_URL = os.environ.get('postgresql://postgres.wtdjcglxtyjbnqslmehj:192829Jc021%40@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres')

app = Flask(__name__)
app.secret_key = os.environ.get('f3305c9d91376b12a4974942ef4231de75530ba3884f5472dab120ee5e514c0b', 'Egenias-Campus-Hardware-Inventory')

SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp-relay.brevo.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_LOGIN = os.environ.get('SMTP_LOGIN', 'bc7d01001@smtp-brevo.com').strip()
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'xsmtpsib-f1fbcecc17655971f97fb4f7220b6cae114a20e19e3bfa6b5cce3f750b869e75-Vo4Yzb1VdNbNZH9h')


def send_otp_email(receiver_email, otp, intent):
    """Sends a 6-digit OTP using Brevo SMTP."""
    if not SMTP_LOGIN or not SMTP_PASSWORD:
        print('Email Error: SMTP_LOGIN and SMTP_PASSWORD must be configured.')
        return False
    msg = MIMEText(
        f'Your {intent} One-Time Password (OTP) is: {otp}\n\n'
        'Please enter this code to proceed. Do not share this code with anyone.'
    )
    msg['Subject'] = f'Laboratory System - {intent} OTP'
    msg['From'] = "egeniascamilo@gmail.com"
    msg['To'] = receiver_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f'Email Error: {type(e).__name__}: {e}')
        app.config['LAST_EMAIL_ERROR'] = f'{type(e).__name__}: {e}'
        return False


class DBConnection:
    '''Compatibility wrapper for SQLite and Supabase PostgreSQL.'''
    def __init__(self):
        self.is_postgres = bool(DATABASE_URL)
        if self.is_postgres:
            if psycopg is None:
                raise RuntimeError('psycopg is required when DATABASE_URL is configured. Run: pip install -r requirements.txt')
            db_url = "postgresql://postgres:192829Jc021%40@db.wtdjcglxtyjbnqslmehj.supabase.co:5432/postgres"
            if 'sslmode=' not in db_url.lower():
                db_url += ('&' if '?' in db_url else '?') + 'sslmode=require'
            self.raw = psycopg.connect(db_url, row_factory=dict_row)
        else:
            self.raw = sqlite3.connect(SQLITE_DATABASE)
            self.raw.row_factory = sqlite3.Row

    def _sql(self, query):
        return query.replace('?', '%s') if self.is_postgres else query

    def execute(self, query, params=None):
        return self.raw.execute(self._sql(query), params or ())

    def commit(self):
        self.raw.commit()

    def close(self):
        self.raw.close()


def db():
    return DBConnection()


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


SEED_HARDWARE = [

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


def init_db():
    conn = db()
    if conn.is_postgres:
        schema = '''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER',
            status TEXT NOT NULL DEFAULT 'ACTIVE'
        );
        CREATE TABLE IF NOT EXISTS hardware (
            item_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            item_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_price DOUBLE PRECISION NOT NULL DEFAULT 0,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS borrow_requests (
            request_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            item_id BIGINT NOT NULL,
            username TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            request_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            return_date TEXT
        );
        CREATE TABLE IF NOT EXISTS reset_requests (
            request_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            request_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reset_password_data (
            request_id BIGINT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );
        '''
        for statement in schema.split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
    else:
        conn.raw.executescript('''
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
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_hardware_item_name ON hardware(item_name)')

    for name, category, qty, price in SEED_HARDWARE:
        if not conn.execute('SELECT item_id FROM hardware WHERE item_name=?', (name,)).fetchone():
            conn.execute(
                'INSERT INTO hardware(item_name,category,quantity,unit_price,status) VALUES(?,?,?,?,?)',
                (name, category, qty, price, status_for(qty))
            )

    admin = conn.execute('SELECT user_id FROM users WHERE username=?', ('admin',)).fetchone()
    admin_hash = generate_password_hash('Admin@123')
    if not admin:
        conn.execute(
            'INSERT INTO users(username,email,password,role,status) VALUES(?,?,?,?,?)',
            ('admin', 'admin@campus.local', admin_hash, 'ADMIN', 'ACTIVE')
        )
    else:
        conn.execute(
            "UPDATE users SET email=?, password=?, role='ADMIN', status='ACTIVE' WHERE username='admin'",
            ('admin@campus.local', admin_hash)
        )
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
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm = request.form.get('confirm_password', '').strip()

    if not username or not email or not password or not confirm:
        flash('All registration fields are required.', 'danger')
        return redirect(url_for('register'))
    if len(password) < 8:
        flash('Password must contain at least 8 characters.', 'warning')
        return redirect(url_for('register'))
    if password != confirm:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('register'))

    conn = db()
    existing = conn.execute(
        'SELECT user_id FROM users WHERE username=? OR email=?',
        (username, email)
    ).fetchone()
    conn.close()
    if existing:
        flash('Username or email already exists.', 'danger')
        return redirect(url_for('register'))

    otp = str(random.randint(100000, 999999))
    session['pending_user'] = {
        'username': username, 'email': email, 'password': password,
        'role': 'USER', 'otp': otp
    }

    if send_otp_email(email, otp, intent='Account Registration'):
        flash('We sent a 6-digit code to your email. Please verify.', 'info')
        return redirect(url_for('verify_otp', action='register'))

    session.pop('pending_user', None)
    email_error = app.config.get('LAST_EMAIL_ERROR', 'Unknown SMTP error')
    flash(f'Failed to send OTP email: {email_error}', 'danger')
    return redirect(url_for('register'))


@app.route('/reset-request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'GET':
        return render_template('reset.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not username or not email or not new_password or not confirm_password:
        flash('All reset fields are required.', 'danger')
        return redirect(url_for('reset_request'))
    if len(new_password) < 8:
        flash('New password must contain at least 8 characters.', 'warning')
        return redirect(url_for('reset_request'))
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('reset_request'))

    conn = db()
    user = conn.execute(
        'SELECT * FROM users WHERE username=? AND email=?',
        (username, email)
    ).fetchone()
    if not user:
        conn.close()
        flash('No matching account was found.', 'danger')
        return redirect(url_for('reset_request'))

    existing = conn.execute(
        "SELECT request_id FROM reset_requests WHERE username=? AND status='PENDING'",
        (username,)
    ).fetchone()
    conn.close()

    if existing:
        flash('You already have a pending password request.', 'warning')
        return redirect(url_for('reset_request'))

    otp = str(random.randint(100000, 999999))
    session['pending_reset'] = {
        'username': username, 'email': email,
        'new_password': new_password, 'otp': otp
    }

    if send_otp_email(email, otp, intent='Password Reset'):
        flash('We sent a 6-digit code to your email. Please verify.', 'info')
        return redirect(url_for('verify_otp', action='reset'))

    session.pop('pending_reset', None)
    email_error = app.config.get('LAST_EMAIL_ERROR', 'Unknown SMTP error')
    flash(f'Failed to send OTP email: {email_error}', 'danger')
    return redirect(url_for('reset_request'))


@app.route('/verify-otp/<action>', methods=['GET', 'POST'])
def verify_otp(action):
    if action not in ('register', 'reset'):
        flash('Invalid verification action.', 'danger')
        return redirect(url_for('login'))

    session_key = 'pending_user' if action == 'register' else 'pending_reset'
    if session_key not in session:
        flash('Session expired. Please try again.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_otp = request.form.get('otp_code', '').strip()
        data = session[session_key]

        if user_otp == data.get('otp'):
            if action == 'register':
                conn = db()
                try:
                    conn.execute(
                        'INSERT INTO users(username,email,password,role,status) VALUES(?,?,?,?,?)',
                        (data['username'], data['email'],
                         generate_password_hash(data['password']),
                         data.get('role', 'USER'), 'ACTIVE')
                    )
                    conn.commit()
                except Exception as e:
                    conn.close()
                    print(f'Registration error: {e}')
                    flash('Username or email already exists.', 'danger')
                    return redirect(url_for('register'))
                conn.close()
                session.pop(session_key, None)
                flash('Account successfully verified and created!', 'success')
                return redirect(url_for('login'))

            conn = db()
            try:
                insert_sql = (
                    'INSERT INTO reset_requests(username,email,status,request_date) '
                    'VALUES(?, ?, ?, ?)'
                )
                if conn.is_postgres:
                    cur = conn.execute(insert_sql + ' RETURNING request_id',
                                       (data['username'], data['email'], 'PENDING',
                                        date.today().isoformat()))
                    request_id = cur.fetchone()['request_id']
                else:
                    cur = conn.execute(insert_sql,
                                       (data['username'], data['email'], 'PENDING',
                                        date.today().isoformat()))
                    request_id = cur.lastrowid

                conn.execute(
                    'INSERT INTO reset_password_data(request_id,password_hash) VALUES(?,?)',
                    (request_id, generate_password_hash(data['new_password']))
                )
                conn.commit()
            except Exception as e:
                conn.close()
                print(f'Reset request error: {e}')
                flash('Could not submit the password reset request.', 'danger')
                return redirect(url_for('reset_request'))
            conn.close()
            session.pop(session_key, None)
            flash('Email verified! Your password reset request has been submitted.', 'success')
            return redirect(url_for('login'))

        flash('Invalid OTP code. Try again.', 'danger')

    return render_template('otp_verify.html', action=action,
                           action_url=url_for('verify_otp', action=action))


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
        except Exception:
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
            conn.commit(); conn.close()
            flash('Borrow request submitted.', 'success'); return redirect(url_for('inventory'))
    conn.close(); return render_template('borrow.html', item=item)


@app.route('/my-borrows')
@login_required
def my_borrows():
    conn = db()
    rows = conn.execute('''SELECT b.*,h.item_name FROM borrow_requests b JOIN hardware h ON h.item_id=b.item_id
                           WHERE b.username=? ORDER BY b.request_id DESC''',
                        (session['username'],)).fetchall()
    conn.close()
    return render_template('my_borrows.html', requests=rows)


@app.post('/return/<int:request_id>')
@login_required
def request_return(request_id):
    conn = db()
    row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND username=?',
                       (request_id, session['username'])).fetchone()
    if row and row['status'] == 'BORROWED':
        conn.execute("UPDATE borrow_requests SET status='RETURN_PENDING' WHERE request_id=?", (request_id,))
        conn.commit(); flash('Return request submitted.', 'success')
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
    return render_template('admin_approvals.html', borrow_requests=borrows,
                           return_requests=returns, reset_requests=resets)


@app.post('/approvals/borrow/<int:request_id>/approve')
@admin_required
def approve_borrow(request_id):
    conn = db()
    row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND status="PENDING"', (request_id,)).fetchone()
    if row:
        item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (row['item_id'],)).fetchone()
        if item and item['quantity'] >= row['quantity']:
            new_qty = item['quantity'] - row['quantity']
            conn.execute('UPDATE hardware SET quantity=?,status=? WHERE item_id=?',
                         (new_qty, status_for(new_qty), item['item_id']))
            conn.execute("UPDATE borrow_requests SET status='BORROWED' WHERE request_id=?", (request_id,))
            conn.commit(); flash('Borrow request approved.', 'success')
        else:
            flash('Not enough stock to approve this request.', 'danger')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/borrow/<int:request_id>/reject')
@admin_required
def reject_borrow(request_id):
    conn = db()
    conn.execute("UPDATE borrow_requests SET status='REJECTED' WHERE request_id=? AND status='PENDING'", (request_id,))
    conn.commit(); conn.close(); flash('Borrow request rejected.', 'success')
    return redirect(url_for('admin_approvals'))


@app.post('/approvals/return/<int:request_id>/approve')
@admin_required
def approve_return(request_id):
    conn = db()
    row = conn.execute('SELECT * FROM borrow_requests WHERE request_id=? AND status="RETURN_PENDING"', (request_id,)).fetchone()
    if row:
        item = conn.execute('SELECT * FROM hardware WHERE item_id=?', (row['item_id'],)).fetchone()
        new_qty = item['quantity'] + row['quantity']
        conn.execute('UPDATE hardware SET quantity=?,status=? WHERE item_id=?',
                     (new_qty, status_for(new_qty), item['item_id']))
        conn.execute("UPDATE borrow_requests SET status='RETURNED',return_date=? WHERE request_id=?",
                     (date.today().isoformat(), request_id))
        conn.commit(); flash('Return approved and stock restored.', 'success')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/return/<int:request_id>/reject')
@admin_required
def reject_return(request_id):
    conn = db()
    conn.execute("UPDATE borrow_requests SET status='BORROWED' WHERE request_id=? AND status='RETURN_PENDING'", (request_id,))
    conn.commit(); conn.close(); flash('Return request rejected.', 'success')
    return redirect(url_for('admin_approvals'))


@app.post('/approvals/password/<int:request_id>/approve')
@admin_required
def approve_reset(request_id):
    conn = db()
    req = conn.execute("SELECT * FROM reset_requests WHERE request_id=? AND status='PENDING'", (request_id,)).fetchone()
    pw = conn.execute('SELECT * FROM reset_password_data WHERE request_id=?', (request_id,)).fetchone()
    if req and pw:
        conn.execute('UPDATE users SET password=? WHERE username=? AND email=?',
                     (pw['password_hash'], req['username'], req['email']))
        conn.execute("UPDATE reset_requests SET status='APPROVED' WHERE request_id=?", (request_id,))
        conn.execute('DELETE FROM reset_password_data WHERE request_id=?', (request_id,))
        conn.commit(); flash('Password request approved.', 'success')
    conn.close(); return redirect(url_for('admin_approvals'))


@app.post('/approvals/password/<int:request_id>/reject')
@admin_required
def reject_reset(request_id):
    conn = db()
    conn.execute("UPDATE reset_requests SET status='REJECTED' WHERE request_id=? AND status='PENDING'", (request_id,))
    conn.execute('DELETE FROM reset_password_data WHERE request_id=?', (request_id,))
    conn.commit(); conn.close(); flash('Password request rejected.', 'success')
    return redirect(url_for('admin_approvals'))


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)
