from flask import Flask, render_template, url_for, redirect
from flask import request, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from static.python.regrexValidation import usernameValidation, passwordValidation
import datetime
from flask import send_from_directory

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
            mongo.db.users.insert_one({
                '_id': userCount+1,
                'username': username,
                'password': hash_password,
                'files': []
            })

            mongo.db.counters.update_one({}, {"$inc": {'userCount': 1}})

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
        uploads_dir = '../uploads/'       # files will get stored here

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

        # file is added into 'files' and 'userfiles' collection
        mongo.db.files.insert_one({
            '_id': doc_number,
            'filename': doc_name,
            'owner': session['username'],
            'description': description,
            'recipients': [{
                'username': recipient,
                'datetime': datetime.datetime.now()
            }]
        }
        )

        mongo.db.users.update_one(
            {'username': recipient},
            {'$addToSet': {'files': {'filename': doc_name, 'status': 0, 'datetime': datetime.datetime.now()}
                           }
             }
        )

        # update counters in the database
        mongo.db.counters.update_one({}, {'$inc': {'fileCount': 1}})
        result = f"file is uploaded successfully! Document id is {doc_name}"
        return render_template('send.html', user=session['username'], success=result)
    else:
        return render_template('send.html', user=session['username'])


@app.route('/received', methods=['GET', 'POST'])
def received():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        option = int(request.form['options'])
        if (option == 1):
            cursor = mongo.db.users.find_one_or_404(
                {'username': session['username'], 'files.status': 0})['files']
        elif (option == 2):
            cursor = mongo.db.users.find_one_or_404(
                {'username': session['username'], 'files.status': 1})['files']
        else:
            return "select an option"
        return render_template('received.html', user=session['username'], option=option, cursor=cursor, mongo=mongo)
    else:
        return render_template('received.html', user=session['username'])


@app.route('/changeStatus/<filename>')
def changeStatus(filename):
    if 'username' not in session:
        return redirect(url_for('index'))
    else:
        if (filename == ''):
            return "There is nothing new !"
        # '$' acts as a positional operator
        mongo.db.users.update_one(
            {
                'username': session['username'],
                'files.filename': filename
            },
            {
                '$set': {
                    'files.$.status': 1
                }
            }
        )
        return "status changed!"


@app.route('/download/<filename>')
def download(filename):
    if 'username' not in session:
        return redirect(url_for('index'))
    else:
        uploads_dir = '../uploads/'
        return send_from_directory(directory=uploads_dir, filename=filename)
    return "Error!"


@app.route('/forward', methods=['GET', 'POST'])
def forward():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        filename = request.form['filename']
        recipient = request.form['recipient']
        remark = request.form['remark']
        error = None

        if (filename == ''):
            error = "Filename shouldn't be empty!"
            return render_template('forward.html', error=error)
        elif (remark == ''):
            error = "Add a remark!"
            return render_template('forward.html', error=error)

        if (mongo.db.users.find_one({'username': session['username'], 'files.filename': filename})):
            return "hello"
        else:
            error = f"There is no file of name {filename}"

        mongo.db.files.update_one(
            {'filename': filename},
            {'$addToSet':
                {
                    'recipients': {'username': recipient, 'datetime': datetime.datetime.now()}
                }
             }
        )

        return render_template('forward.html', error=error)
    else:
        return render_template('forward.html')


@app.route('/track')
def track():
    return "track"


if __name__ == '__main__':
    app.run(debug=True)
