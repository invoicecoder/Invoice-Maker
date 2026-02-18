from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
REAL_PASSWORD = os.environ.get("APP_PASSWORD")

@app.route("/health")
def health():
    return "OK", 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged in'):
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        password = request.form['password']

        if password == REAL_PASSWORD:   # Change this!
            session['logged_in'] = True
            return render_template("loading.html", redirect_url=url_for('index'))

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

# ... rest of your code ...

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

























