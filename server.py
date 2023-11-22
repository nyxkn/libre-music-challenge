#!/usr/bin/env python3

from flask import Flask, request, render_template, redirect, url_for, make_response
import flask_login
from werkzeug.security import generate_password_hash, check_password_hash
import internetarchive
from tinydb import TinyDB, Query
import csv
from datetime import datetime
import markdown
import feedgenerator
import common as c
import os
import json
from typing import List, Dict, Tuple, Optional, Union
# import re

app = Flask(__name__)


with open("secret/secret_key", "r") as file:
    app.secret_key = file.read().rstrip()


login_manager = flask_login.LoginManager()
login_manager.init_app(app)


def main():
    app.run(debug=True)


# ================================================================================
# AUTH
# ================================================================================

class User(flask_login.UserMixin):
    pass


def user_exists(username):
    db = TinyDB(c.users_db)
    # db.update(set_vote(artist, vote), Query().user == user)
    query_data = db.search(Query().username == username)

    if len(query_data) == 1:
        return True
    return False


def create_user(username, password):
    db = TinyDB(c.users_db)
    db.insert({'username': username, 'password': generate_password_hash(password)})


def update_password(username, new_password):
    db = TinyDB(c.users_db)
    db.update({'password': generate_password_hash(new_password)}, Query().username == username)


# returns error message. empty string for ok
def update_or_create_user_if_needed(username, password) -> str:
    db = TinyDB(c.users_db)
    query_data = db.search(Query().username == username)

    if len(query_data) == 1:
        if query_data[0]['password'] == '':
            # update password
            # after the password is cleared from the database (i.e. = ""), it can be reset
            update_password(username, password)
    else:
        # user not in database, so create user
        available_usernames = c.get_available_usernames()
        # query_data = db.search(Query().username.matches(username, flags=re.IGNORECASE))
        if not username in available_usernames:
            return "Cannot register with this username. If you're not a participant but want to vote, let us know and we'll enable an account for you."
        else:
            create_user(username, password)

    return ""



def try_login(username, password):
    db = TinyDB(c.users_db)
    query_data = db.search(Query().username == username)

    def authenticate_user(username):
        user = User()
        user.id = username
        flask_login.login_user(user)

    if check_password_hash(query_data[0]['password'], password):
        authenticate_user(username)
        return True
    else:
        return False


# def password_exists(username, password):
#     db = TinyDB(c.users_db)
#     query_data = db.search(Query().username == username)

#     if len(query_data) == 1 and query_data[0]['password'] == '':
#         return True
#     return False


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

        if not username or not password:
            return 'Input a username and a password'

        if not username.isalnum():
            return "Username should be only letters and numbers"

        username = username.lower()

        error = update_or_create_user_if_needed(username, password)

        if error:
            return error

        if try_login(username, password):
            return redirect(url_for('vote'))

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


def user_is_authenticated():
    return flask_login.current_user.is_authenticated


def get_events():
    events = []
    with open(c.events_datafile, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            events.append(row)

    return events


def get_event(event_id: int) -> Dict:
    for e in get_events():
        if e['event'] == str(event_id):
            return e
    return {}


def is_event_id_valid(event_id):
    if get_event(event_id) != {}:
        return True
    return False


def get_current_user():
    return flask_login.current_user.id


def to_date_object(date_str):
    return datetime.strptime(date_str, "%d/%m/%y")


def get_month_and_year(date_str):
    date_object = to_date_object(date_str)

    # Extract the month name and year number from the datetime object
    month_name = date_object.strftime("%B")
    year_number = date_object.strftime("%Y")

    # Create the formatted string
    result = f"{month_name} {year_number}"

    return result


def markdown_to_html(markdown_text):
    html = markdown.markdown(markdown_text)
    return html


def read_text_file(file_path):
    with open(file_path, 'r') as file:
        contents = file.read()
    return contents


# ================================================================================
# API - PUBLIC
# ================================================================================


@app.route("/get_entries/<int:event_id>", methods=["GET"])
def get_entries(event_id: int):
    if not is_event_id_valid(event_id):
        return "Invalid event ID"

    item = internetarchive.get_item("libre-music-challenge-" + str(event_id))

    allowed_formats = [".flac", ".ogg"]
    entries = []
    for file in item.files:
        if file["source"] == "original":
            allowed = False
            for ext in allowed_formats:
                if file["name"].endswith(ext):
                    allowed = True
                    break
            if allowed:
                entry = os.path.splitext(file["name"])[0].split(" - ")
                # we should maybe convert artist to username in here and send that along?
                # but maybe more chances to go wrong
                entries.append({"artist": entry[0], "track": entry[1], "filename": file["name"]})

    return entries


@app.route("/ping")
def ping():
    return "pong"


# ================================================================================
# API - PRIVATE
# ================================================================================


# needs reviewing. but likely not needed
# @app.route("/save_vote", methods=["POST"])
# @flask_login.login_required
# def save_vote():
#     if is_voting_locked():
#         return {}

#     artist = ""
#     vote = ""
#     # there's actually only one entry
#     for k,v in request.form.items():
#         if k.startswith("vote"):
#             artist = k.replace("vote_", "")
#             vote = v
#             break

#     db = get_db(get_current_event())

#     user = get_current_user()

#     def set_vote(artist, new_vote):
#         def transform(doc):
#             doc['votes'][artist] = new_vote
#         return transform

#     db.update(set_vote(artist, vote), Query().user == user)

#     return {"status": "ok"}



@app.route("/save_votes", methods=["POST"])
@flask_login.login_required
def save_votes():
    # get_json() for regular post
    # form for form post
    # args for get url params

    if not c.is_voting_open():
        return {}

    user_votes = {}
    for k,v in request.form.items():
        if k.startswith("vote"):
            artist = k.replace("vote_", "")
            vote = v
            user_votes[artist] = vote


    db = c.get_votes_db(c.get_current_voting_event())

    user = get_current_user()
    db.upsert({"user": user, "votes": user_votes}, Query().user == user)

    return {}



@app.route("/get_my_votes/<int:event_id>", methods=["POST"])
@flask_login.login_required
def get_user_votes(event_id: int):
    if not is_event_id_valid(event_id):
        return "Invalid event ID"

    db = c.get_votes_db(event_id)
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
    return render_template("index.html")


@app.route("/rss")
def rss():
    events = get_events()

    # Create a feed object
    # or use Atom1Feed for an atom feed. both have the same api, also for add_item
    # feed = feedgenerator.Atom1Feed(
    feed = feedgenerator.Rss201rev2Feed(
        title='Libre Music Challenge',
        link='https://lmc.nyxkn.org',
        description='Announcements for the monthly Libre Music Challenge',
        language='en',
    )

    for event in events:
        date_obj = datetime.strptime(event["date"], '%d/%m/%y')
        month_year = date_obj.strftime('%B %Y')
        feed.add_item(
            title=f'"{event["title"]}" - LMC #{event["event"]} ({month_year})',
            link=event["link"],
            description=f'The theme for the month of {month_year} is: {event["title"]}\n{event["link"]}',
            unique_id=event["event"],
            pubdate=to_date_object(event["date"]),
        )

    # Generate the XML for the feed
    rss_feed = feed.writeString('utf-8')

    response = make_response(rss_feed)
    # set atom+xml in case of atom
    response.headers['Content-Type'] = 'application/rss+xml'
    response.headers['Content-Disposition'] = 'inline; filename=feed.rss'
    return response


@app.route("/rules")
def rules():
    rules = read_text_file(c.rules_md)
    html_output = markdown_to_html(rules)
    return render_template("rules.html", rules_html=html_output)


@app.route("/vote")
def vote():
    if user_is_authenticated():
        return render_template(
            "vote.html",
            event_id=c.get_current_voting_event(),
            locked=(not c.is_voting_open()),
            user=get_current_user()
        )
    else:
        return render_template("login.html")


@app.route("/load_current_entries", methods=["GET"])
def load_current_entries():
    current_event = c.get_current_voting_event()

    if current_event == 0:
        return {}
    else:
        votes = get_user_votes(current_event)
        return render_template(
            "entries.html",
            event_id=current_event,
            entries=get_entries(current_event),
            votes=votes,
            locked=(not c.is_voting_open())
        )


@app.route('/events', methods=["GET"])
def events():
    events = get_events()
    for event in events:
        event['month_date'] = get_month_and_year(event['date'])
        event['winner'] = event['winner'].replace("\n", ", ")
        # event['archive'] = event['archive'].replace("---", "")

    events.reverse()
    return render_template("events.html", events=events)


@app.route('/results/<int:event_id>', methods=["GET"])
def results(event_id: int):
    event = get_event(event_id)
    if event == {}:
        return "Invalid event ID"

    if event['winner'] == "?":
        return "Results not yet announced"

    results = {}
    filename = f"{c.results_path}/lmc{event_id}-scoreboard.json"
    if not os.path.exists(filename):
        return "Missing results data for this event"

    with open(filename, 'r') as json_file:
        results = json.load(json_file)

    admin_user = ""
    with open("secret/admin_user", "r") as file:
        admin_user = file.read().rstrip()

    admin = False
    if user_is_authenticated() and get_current_user() == admin_user:
        admin = True

    return render_template("results.html", event_id=event_id, results=results, admin=admin)


if __name__ == "__main__":
    main()
