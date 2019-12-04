from flask import Flask, render_template, url_for, redirect
from flask import request, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import secure_filename
import os
from static.python.regrexValidation import usernameValidation, passwordValidation
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32) or "328eb7fef17d4a099ea990b997ec1405"
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if (mongo.db.users.find_one({'username': username})):
            if (username == mongo.db.users.find_one({'username': username})['username']) and check_password_hash(mongo.db.users.find_one({'username': username})['password'], password):
                session['username'] = username
                return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login')
def login():
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
        return "<strong>You have been logged out!</strong>"
    else:
        return "<strong>You're already logged out!</strong>"


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # password validation --------------->>>>>>>>>>>>>>>
        if (usernameValidation(username) == False):
            error = "Username doesn't meet the requirements!"
            return render_template('register.html', error=error)
        elif (passwordValidation(password) == False or passwordValidation(confirm_password) == False):
            error = "Password doesn't meet the criteria!"
            return render_template('register.html', error=error)
        elif (password != confirm_password):
            error = "Password doesnot match!"
            return render_template('register.html', error=error)
        elif (mongo.db.users.find_one({'username': username})):
            error = "Username already exists!"
            return render_template('register.html', error=error)
        else:
            userCount = mongo.db.counters.find_one_or_404({})['userCount']
            hash_password = generate_password_hash(password)
            mongo.db.users.insert_one(
                {'_id': userCount+1, 'username': username, 'password': hash_password})
            mongo.db.counters.update({}, {"$inc": {'userCount': 1}})
            return "user successfully created!  <a href='/login' >Log In </a> to continue..."
    return render_template('register.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    else:
        return render_template('dashboard_base.html', user=session['username'])


@app.route('/send', methods=['GET', 'POST'])
def send():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        recipient = request.form['recipient']
        description = request.form['description']
        file_obj = request.files['filename']    # file object is created
        uploads_dir = './static/uploads/'       # files will get stored here

        if (recipient and description and file_obj):
            pass
        else:
            error = "Each field is mandatory"
            return render_template('send.html', user=session['username'], error=error)

        if (mongo.db.users.find_one({'username': recipient})):
            pass
        else:
            error = "Recipient is unknown"
            return render_template('send.html', user=session['username'], error=error)

        # extract counters from database
        doc_number = mongo.db.counters.find_one_or_404({})['fileCount']
        doc_number += 1

        # extract file extension from the original filename
        file_extension = os.path.splitext(file_obj.filename)[1]

        # sequencial file renaming
        doc_name = 'DOC' + str(int(doc_number)) + file_extension
        file_obj.save(uploads_dir + doc_name)

        # file is added into database
        # mongo.db.files.insert_one({'filename': doc_number, 'owner': session['username'], 'recipients': [
        #                          {'user': recipient, 'datetime': datetime.datetime.now()}]})

        mongo.db.files.insert_one({
            '_id': doc_number,
            'filename': doc_name,
            'owner': session['username'],
            'description': description,
            'recipients': {
                'username': recipient,
                'datetime': datetime.datetime.now()
            }
        }
        )

        # update counters in the database
        mongo.db.counters.update({}, {'$inc': {'fileCount': 1}})
        result = f"file is uploaded successfully! Document id is {doc_number}"
        return render_template('send.html', user=session['username'], success=result)
    else:
        return render_template('send.html', user=session['username'])


if __name__ == '__main__':
    app.run(debug=True)
