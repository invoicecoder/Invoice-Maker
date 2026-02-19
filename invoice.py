from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
REAL_PASSWORD = os.environ.get("APP_PASSWORD")

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
        return redirect(url_for('login'))

    user_name = session.get('user_name', "User")
    return render_template('menu.html', user_name=user_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        if password == REAL_PASSWORD:   # Change this!
            session['logged_in'] = True
            session['user_name'] = name
            return render_template("loading.html", redirect_url=url_for('menu'))

        else:
             error = "Incorrect password. Please try again."

    return render_template('login.html', error=error)
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))



@app.route('/', methods=['GET', 'POST'])
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





































