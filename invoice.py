from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

REAL_PASSWORD = os.environ.get("APP_PASSWORD")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------------- Supabase Helper Functions ----------------------

def supabase_get(table, filters=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    resp = requests.get(url, headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

def supabase_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.post(url, headers=HEADERS, data=json.dumps(data))
    return resp.json() if resp.status_code in (200, 201) else None

def supabase_update(table, data, filters):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    resp = requests.patch(url, headers=HEADERS, data=json.dumps(data))
    return resp.json() if resp.status_code in (200, 204) else None

def supabase_delete(table, filters):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    resp = requests.delete(url, headers=HEADERS)
    return resp.status_code in (200, 204)

# ---------------------- User/Invoice Logic ----------------------

def get_user_by_username(username):
    users = supabase_get("users", f"username=eq.{username}")
    return users[0] if users else None

def get_user_by_id(user_id):
    users = supabase_get("users", f"id=eq.{user_id}")
    return users[0] if users else None

def get_invoice_by_id(invoice_id):
    invoices = supabase_get("invoices", f"id=eq.{invoice_id}")
    return invoices[0] if invoices else None

def get_all_invoices():
    return supabase_get("invoices")

# ---------------------- Decorators ----------------------

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        user = get_user_by_id(session.get('user_id'))
        if not user or not user.get('is_admin'):
            return "Access denied", 403
        return f(*args, **kwargs)
    return decorated_function

# ---------------------- Routes ----------------------

@app.route("/health")
def health():
    return "OK", 200

@app.route('/')
def menu():
    if not session.get('logged_in'):
        return redirect(url_for('register'))
    return render_template('menu.html', user_name=session.get('user_name'))

# ---------------------- Registration/Login ----------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect(url_for('menu'))
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        app_password = request.form['app_password']

        if app_password != REAL_PASSWORD:
            error = "Invalid app password."
        elif get_user_by_username(username):
            error = "Username already exists."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            user_data = {
                "username": username,
                "password_hash": generate_password_hash(password),
                "is_admin": False
            }
            supabase_insert("users", user_data)
            return render_template("loading.html", redirect_url=url_for('login'))

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('menu'))

    error = None
    if request.method == 'POST':
        username = request.form['name']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user.get('password_hash', ''), password):
            session['logged_in'] = True
            session['user_name'] = user['username']
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            redirect_url = url_for('admin_menu') if user['is_admin'] else url_for('menu')
            return render_template("loading.html", redirect_url=redirect_url)
        else:
            error = "Incorrect username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------- Admin Routes ----------------------

@app.route('/admin/menu')
@admin_required
def admin_menu():
    users = supabase_get("users")
    return render_template('admin_menu.html', users=users)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = supabase_get("users")
    return render_template('all_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        return "You cannot delete your own account!", 400
    supabase_delete("invoices", f"user_id=eq.{user_id}")
    supabase_delete("users", f"id=eq.{user_id}")
    return redirect(url_for('admin_users'))

@app.route('/admin/invoices')
@admin_required
def admin_invoices():
    invoices = get_all_invoices()
    invoices.sort(key=lambda x: x['id'], reverse=True)
    return render_template('all_invoices.html', invoices=invoices)

# ---------------------- Invoice Routes ----------------------

@app.route('/index', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        data = {
            "user_id": user_id,
            "student_name": request.form['student_name'],
            "parent_name": request.form['parent_name'],
            "tutor_name": request.form['tutor_name'],
            "director_name": request.form['director_name'],
            "director_email": request.form['director_email'],
            "month": request.form['month'],
            "a_fee": int(request.form.get('a_fee', 0) or 0),
            "s_fee": int(request.form.get('s_fee', 0) or 0),
            "f_fee": int(request.form.get('f_fee', 0) or 0),
            "t_fee": int(request.form.get('t_fee', 0) or 0),
            "total": 0,  # computed below
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        data["total"] = data["a_fee"] + data["s_fee"] + data["f_fee"] + data["t_fee"]
        invoice = supabase_insert("invoices", data)
        session['invoice_data'] = data
        return render_template("loading.html", redirect_url=url_for('show_invoice'))

    return render_template('index.html')

@app.route('/invoice')
def show_invoice():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    data = session.get('invoice_data')
    if not data:
        return redirect(url_for('index'))
    return render_template('invoice.html', invoice=data)

@app.route('/invoice/<int:invoice_id>')
def show_invoices(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    invoice = get_invoice_by_id(invoice_id)
    user = get_user_by_id(session['user_id'])
    if not invoice or (not user['is_admin'] and invoice['user_id'] != user['id']):
        return "Access denied", 403
    return render_template('invoice.html', invoice=invoice)

@app.route('/invoices')
def invoices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    all_invoices = get_all_invoices()
    if not user['is_admin']:
        all_invoices = [i for i in all_invoices if i['user_id'] == user['id']]
    all_invoices.sort(key=lambda x: x['id'], reverse=True)
    return render_template('saved_invoices.html', invoices=all_invoices)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        return redirect(url_for('invoices'))
    if not user['is_admin'] and invoice['user_id'] != user['id']:
        return "Access denied", 403

    supabase_delete("invoices", f"id=eq.{invoice_id}")
    return redirect(url_for('invoices'))

# ---------------------- Settings ----------------------

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    error = None
    success = None

    if request.method == 'POST':
        # Change username
        new_username = request.form.get('new_username')
        if new_username:
            if get_user_by_username(new_username):
                error = "Username already taken."
            else:
                supabase_update("users", {"username": new_username}, f"id=eq.{user['id']}")
                session['user_name'] = new_username
                success = "Username updated successfully!"

        # Change password
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if current_password and new_password:
            if not check_password_hash(user['password_hash'], current_password):
                error = "Current password is incorrect."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            elif len(new_password) < 6:
                error = "Password must be at least 6 characters."
            else:
                supabase_update("users", {"password_hash": generate_password_hash(new_password)}, f"id=eq.{user['id']}")
                success = "Password updated successfully!"

    return render_template('settings.html', error=error, success=success, current_username=user['username'])

# ---------------------- Bootstrap Admin ----------------------

@app.before_first_request
def bootstrap_admin():
    admin = get_user_by_username("admin")
    if not admin:
        supabase_insert("users", {
            "username": "admin",
            "password_hash": generate_password_hash(ADMIN_PASSWORD),
            "is_admin": True
        })
with app.app_context():
    bootstrap_admin()
# ---------------------- Run ----------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

























































































