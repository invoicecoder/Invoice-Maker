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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Set password (hash it for security)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Check password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
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
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/menu')
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
            session['user_name'] = username
            return render_template("loading.html", redirect_url=url_for('menu'))
        else:
            # Login failed
            error = "Incorrect username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))



@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('register'))
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
    data = session.get('invoice_data')
    if not data:
        return redirect(url_for('index'))
    return render_template('invoice.html', **data)
@app.route("/debug")
def debug():
    return {
        "APP_PASSWORD_exists": REAL_PASSWORD is not None,
        "SECRET_KEY_exists": app.secret_key is not None
    }



# ... rest of your code ...














































