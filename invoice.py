from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
REAL_PASSWORD = os.environ.get("APP_PASSWORD")
database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    invoices = db.relationship('Invoice', backref='user', lazy=True)

    # Set password (hash it for security)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Check password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    student_name = db.Column(db.String(100))
    parent_name = db.Column(db.String(100))
    tutor_name = db.Column(db.String(100))
    director_name = db.Column(db.String(100))
    director_email = db.Column(db.String(100))
    month = db.Column(db.String(50))

    a_fee = db.Column(db.Integer)
    s_fee = db.Column(db.Integer)
    f_fee = db.Column(db.Integer)
    t_fee = db.Column(db.Integer)
    total = db.Column(db.Integer)

    date = db.Column(db.String(20))

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        user = User.query.get(session.get('user_id'))

        if not user or not user.is_admin:
            return "Access denied", 403

        return f(*args, **kwargs)

    return decorated_function
@app.route('/admin/menu')
@admin_required
def admin_menu():
    users = User.query.all()
    return render_template('admin_menu.html', users=users)
@app.route('/admin/users', endpoint='admin_users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('all_users.html', users=users)
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    # Admin cannot delete themselves accidentally
    if user_id == session['user_id']:
        return "You cannot delete your own account!", 400

    user = User.query.get(user_id)

    if not user:
        return redirect(url_for('admin_users'))

    # Delete all invoices associated with this user first
    Invoice.query.filter_by(user_id=user.id).delete()

    # Then delete the user
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('admin_users'))
@app.route('/admin/invoices')
@admin_required
def admin_invoices():
    invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    return render_template('all_invoices.html', invoices=invoices)
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    error = None
    success = None

    user = User.query.get(session['user_id'])

    if request.method == 'POST':

        # ---------- CHANGE USERNAME ----------
        if 'new_username' in request.form:
            new_username = request.form['new_username'].strip()

            if not new_username:
                error = "Username cannot be empty."

            elif User.query.filter_by(username=new_username).first():
                error = "Username already taken."

            else:
                user.username = new_username
                db.session.commit()
                session['user_name'] = new_username
                success = "Username updated successfully!"

        # ---------- CHANGE PASSWORD ----------
        elif 'current_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if not user.check_password(current_password):
                error = "Current password is incorrect."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            elif len(new_password) < 6:
                error = "Password must be at least 6 characters."
            else:
                user.set_password(new_password)
                db.session.commit()
                success = "Password updated successfully!"
        
    return render_template('settings.html', error=error, success=success, current_username=user.username)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    invoice = Invoice.query.get(invoice_id)

    if not invoice:
        return redirect(url_for('admin_invoices'))

    # Allow admin OR owner
    if not user.is_admin and invoice.user_id != user.id:
        return "Access denied", 403

    db.session.delete(invoice)
    db.session.commit()

    return redirect(url_for('invoices'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect(url_for('menu'))
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        app_password = request.form['app_password']  # Added field

        # Check shared app password
        if app_password != REAL_PASSWORD:
            error = "Invalid app password."
        # Check if username exists
        elif User.query.filter_by(username=username).first():
            error = "Username already exists."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            # Create user
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return render_template("loading.html", redirect_url=url_for('login'))

    return render_template('register.html', error=error)

@app.route("/health")
def health():
    return "OK", 200

@app.route('/')
def menu():
    if not session.get('logged_in'):
        return redirect(url_for('register'))

    user_name = session.get('user_name', "User")
    return render_template('menu.html', user_name=user_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to menu
    if session.get('logged_in'):
        return redirect(url_for('menu'))

    error = None
    if request.method == 'POST':
        username = request.form['name']   # form field for username
        password = request.form['password']

        # Look up user in Postgres
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Login successful
            session['logged_in'] = True
            session['user_name'] = user.username
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            if user.is_admin:
                return render_template("loading.html", redirect_url=url_for('admin_menu'))
            else:
                return render_template("loading.html", redirect_url=url_for('menu'))
        else:
            # Login failed
            error = "Incorrect username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route('/index', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        student_name = request.form['student_name']
        parent_name = request.form['parent_name']
        tutor_name = request.form['tutor_name']
        director_name = request.form['director_name']
        director_email = request.form['director_email']
        month = request.form['month']
        a_fee = int(request.form.get('a_fee', 0) or 0)
        s_fee = int(request.form.get('s_fee', 0) or 0)
        f_fee = int(request.form.get('f_fee', 0) or 0)
        t_fee = int(request.form.get('t_fee', 0) or 0)

        total = a_fee + s_fee + f_fee + t_fee
        date = datetime.now().strftime("%Y-%m-%d")
        user = User.query.filter_by(username=session['user_name']).first()

        new_invoice = Invoice(
        user_id=user.id,
        student_name=student_name,
        parent_name=parent_name,
        tutor_name=tutor_name,
        director_name=director_name,
        director_email=director_email,
        month=month,
        a_fee=a_fee,
        s_fee=s_fee,
        f_fee=f_fee,
        t_fee=t_fee,
        total=total,
        date=date
    )

        db.session.add(new_invoice)
        db.session.commit()
        session['invoice_data'] = {
            "student_name": student_name,
            "parent_name": parent_name,
            "tutor_name": tutor_name,
            "director_name": director_name,
            "director_email": director_email,
            "month": month,
            "a_fee": a_fee,
            "s_fee": s_fee,
            "f_fee": f_fee,
            "t_fee": t_fee,
            "date": date,
            "total": total
        }

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

    user = User.query.get(session['user_id'])
    invoice = Invoice.query.get_or_404(invoice_id)

    # Allow admin OR owner
    if not user.is_admin and invoice.user_id != user.id:
        return "Access denied", 403

    return render_template('invoice.html', invoice=invoice)
@app.route('/invoices')
def invoices():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.is_admin:
        all_invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    else:
        all_invoices = Invoice.query.filter_by(user_id=user.id)\
                                    .order_by(Invoice.id.desc()).all()

    return render_template('saved_invoices.html', invoices=all_invoices)

with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
    if not admin:
        admin = User(username="admin")

    admin.is_admin = True
    admin.set_password(ADMIN_PASSWORD)  # choose your real password

    db.session.add(admin)
    db.session.commit()






















































































