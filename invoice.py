from flask import Flask, render_template, request
from datetime import datetime
import random
import os

app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == "yourpassword":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return "Login Page"




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

        return render_template('invoice.html',
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
                               date=date,
                               total=total)


    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)









