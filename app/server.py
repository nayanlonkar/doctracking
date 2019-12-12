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
        docType = request.form['docType']
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
            'docType': docType,
            'recipients': [{
                'username': recipient,
                'sender': session['username'],
                'datetime': datetime.datetime.now(),
                'remark': description
            }]
        }
        )

        mongo.db.users.update_one(
            {'username': recipient},
            {'$addToSet': {'files': {'filename': doc_name, 'sender': session['username'], 'docType': docType, 'status': 0, 'datetime': datetime.datetime.now()}
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
        # option = int(request.form['options'])
        option = request.form.get('options')
        docType = request.form.get('docType')

        return f"{docType}"
        if (option == None):
            return "select an option!"
        else:
            option = int(option)

        cursor = None
        if (option == 1):
            if (mongo.db.users.find_one({'username': session['username'], 'files.status': 0})):
                cursor = mongo.db.users.find_one(
                    {'username': session['username'], 'files.status': 0})['files']
        elif (option == 2):
            if (mongo.db.users.find_one({'username': session['username'], 'files.status': 1})):
                cursor = mongo.db.users.find_one(
                    {'username': session['username'], 'files.status': 1})['files']
        else:
            pass

        if (cursor == None):
            error = "No file found"
            return render_template('received.html', user=session['username'], error=error, mongo=mongo)

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
        return "file recieved!"


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
            return render_template('forward.html', user=session['username'], error=error)
        elif (remark == ''):
            error = "Add a remark!"
            return render_template('forward.html', user=session['username'], error=error)

        if (mongo.db.users.find_one({'username': session['username'], 'files.filename': filename})):
            pass
        else:
            error = f"There is no file of name {filename}"
            return render_template('forward.html', user=session['username'], error=error)

        if (mongo.db.users.find_one({'username': recipient})):
            pass
        else:
            error = f"There is no user {recipient}"
            return render_template('forward.html', user=session['username'], error=error)

        if (mongo.db.files.find_one({'filename': filename})):
            docType = mongo.db.files.find_one(
                {'filename': filename})['docType']

        mongo.db.files.update_one(
            {'filename': filename},
            {'$addToSet':
                {
                    'recipients': {'username': recipient, 'sender': session['username'], 'datetime': datetime.datetime.now(), 'remark': remark}
                }
             }
        )

        mongo.db.users.update_one(
            {'username': recipient},
            {'$addToSet': {'files': {'filename': filename, 'sender': session['username'], 'docType': docType, 'status': 0, 'datetime': datetime.datetime.now()}
                           }
             }
        )

        success = "file forwarded successfully!"
        return render_template('forward.html', user=session['username'], error=error, success=success)
    else:
        return render_template('forward.html', user=session['username'])


@app.route('/track', methods=['GET', 'POST'])
def track():
    if 'username' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        filename = request.form['filename']
        error = None

        if (mongo.db.files.find_one({'filename': filename, 'owner': session['username']})):
            pass
        else:
            error = 'Either file does not found or You are not authorised to track this file!'
            return render_template('track.html', user=session['username'], error=error)

        cursor = mongo.db.files.find_one_or_404(
            {'filename': filename})['recipients']
        return render_template('track.html', user=session['username'], cursor=cursor)

    else:
        return render_template('track.html', user=session['username'])


if __name__ == '__main__':
    app.run(debug=True)
