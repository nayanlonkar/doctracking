from flask import Flask, render_template, url_for, redirect, g
from flask import request, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash
import os
from static.python.regrexValidation import usernameValidation, passwordValidation

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32) or "328eb7fef17d4a099ea990b997ec1405"
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if (usernameValidation(username) == False):
            error = "username doesn't meet the criteria"
            return render_template('register.html', error=error)
        if (passwordValidation(password) == False or passwordValidation(confirm_password) == False):
            error = "username doesn't meet the criteria"
            return render_template('register.html', error=error)
        return "hello"
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return "<h2>dashboard</h2>"
    else:
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
