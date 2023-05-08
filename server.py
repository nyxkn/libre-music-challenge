#!/usr/bin/env python3

from flask import Flask, request, render_template, redirect, url_for, make_response
import flask_login
from internetarchive import get_item
from tinydb import TinyDB, Query, table, operations
# from flask_assets import Bundle, Environment
from pprint import pprint


app = Flask(__name__)

# python -c 'import secrets; print(secrets.token_hex())'
# app.secret_key = ""

with open("secret/secret_key", "r") as file:
    app.secret_key = file.read().rstrip()


login_manager = flask_login.LoginManager()
login_manager.init_app(app)


# mock database
# app.config['users'] = {
#     'arst': {'password': 'qwfp'},
#     'qwfp': {'password': 'qwfp'}
# }


def main():
    app.run(debug=True)


# ================================================================================
# AUTH
# ================================================================================

class User(flask_login.UserMixin):
    pass

def user_exists(username):
    db = TinyDB("data/users.json")
    # db.update(set_vote(artist, vote), Query().user == user)
    query_data = db.search(Query().username == username)

    if len(query_data) == 1:
    # if username in app.config['users']:
        return True
    return False

def create_user(username, password):
    db = TinyDB("data/users.json")
    db.insert({'username': username, 'password': password})
    # app.config['users'][username] = { 'password': password }


def check_user_auth(username, password):
    db = TinyDB("data/users.json")
    query = Query()
    query_data = db.search((query.username == username) & (query.password == password))

    # if username in app.config['users'] and password == app.config['users'][username]['password']:
    if len(query_data) == 1:
        return True
    return False


@login_manager.user_loader
def user_loader(username):
    if not user_exists(username):
        return

    user = User()
    user.id = username
    return user


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')

    if not user_exists(username):
        return

    user = User()
    user.id = username
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")

    # requires POST to be in form format (-f in httpie)
    if "username" in request.form:
        username = request.form['username']
        password = request.form['password']

        # TODO: remove
        allow_any_user = True
        if allow_any_user:
            if username and not user_exists(username):
                create_user(username, password)

        if check_user_auth(username, password):
            user = User()
            user.id = username
            flask_login.login_user(user)
            return redirect(url_for('home'))

    return 'Bad login'


@app.route('/login-status', methods=["GET"])
@flask_login.login_required
def protected():
    return 'Logged in as: ' + flask_login.current_user.id


@app.route('/logout', methods=["GET", "POST"])
def logout():
    flask_login.logout_user()

    response = make_response('Logged out')
    response.headers['HX-Redirect'] = '/'
    return response

    # return 'Logged out'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized', 401


# ================================================================================
# UTILS
# ================================================================================

def get_db(event_id: int):
    db = TinyDB("data/db.json")
    table = db.table(str(event_id))
    # this call is required to setup the table in case it's empty (?)
    table.all()

    return table

def get_current_user():
    return flask_login.current_user.id



# event = 0 in current_event file to disable voting and showing
# locked = 1 to disable changing votes
# eventually make it automatic depending on date

def get_current_event():
    current_event = 0

    # with open("current_event", "r") as file:
    #     contents = file.read()
    #     current_event = int(contents.rstrip())

    with open("data/current_event", "r") as file:
        lines = [line.strip() for line in file.readlines()]
        current_event = int(lines[0])

    return current_event


def is_voting_locked():
    locked = 1
    with open("data/current_event", "r") as file:
        lines = [line.strip() for line in file.readlines()]
        locked = int(lines[1])

    return locked

# ================================================================================
# API - PUBLIC
# ================================================================================


@app.route("/get_entries/<int:event_id>", methods=["GET"])
def get_entries(event_id: int):
    item = get_item("libre-music-challenge-" + str(event_id))

    entries = []
    for file in item.files:
        if file["source"] == "original" and file["name"].endswith(".flac"):
            entry = file["name"].replace(".flac", "").split(" - ")
            entries.append({"artist": entry[0], "track": entry[1], "filename": file["name"]})

    return entries


@app.route("/ping")
def ping():
    return "pong"


# ================================================================================
# API - PRIVATE
# ================================================================================


@app.route("/save_vote", methods=["POST"])
@flask_login.login_required
def save_vote():
    if is_voting_locked():
        return {}

    artist = ""
    vote = ""
    # there's actually only one entry
    for k,v in request.form.items():
        if k.startswith("vote"):
            artist = k.replace("vote_", "")
            vote = v
            break

    db = get_db(get_current_event())

    user = flask_login.current_user.id

    def set_vote(artist, new_vote):
        def transform(doc):
            doc['votes'][artist] = new_vote
        return transform

    db.update(set_vote(artist, vote), Query().user == user)

    return {"status": "ok"}



@app.route("/save_votes", methods=["POST"])
@flask_login.login_required
def save_votes():
    # get_json() for regular post
    # form for form post
    # args for get url params

    if is_voting_locked():
        return {}

    user_votes = {}
    for k,v in request.form.items():
        if k.startswith("vote"):
            artist = k.replace("vote_", "")
            vote = v
            user_votes[artist] = vote


    db = get_db(get_current_event())

    user = get_current_user()
    db.upsert({"user": user, "votes": user_votes}, Query().user == user)

    return {}



@app.route("/get_my_votes/<int:event_id>", methods=["POST"])
@flask_login.login_required
def get_user_votes(event_id: int):
    db = get_db(event_id)
    db_data = db.search(Query().user == get_current_user())

    votes = {}
    if len(db_data) > 0:
        votes = db_data[0]["votes"]
    # else:
    #     print("initializing db entry for ", get_current_user(), event_id)
    #     # this initializes the db entry (with empty votes)
    #     save_votes()

    return votes


# ================================================================================
# WEBSITE
# ================================================================================



@app.route("/")
def home():
    if flask_login.current_user.is_authenticated:
        return render_template("index.html", event_id=get_current_event(), locked=is_voting_locked(), user=get_current_user())
    else:
        return render_template("login.html")



@app.route("/load_current_entries", methods=["GET"])
def load_current_entries():
    current_event = get_current_event()

    if current_event == 0:
        return {}

    else:
        votes = get_user_votes(current_event)
        return render_template(
            "entries.html",
            event_id=current_event, entries=get_entries(current_event), votes=votes, locked=is_voting_locked())


if __name__ == "__main__":
    main()
