#!/usr/bin/env python3

from tinydb import TinyDB
import yaml

users_db = "storage/users.json"
votes_db = "storage/votes.json"
current_voting_event_statusfile = "storage/current_voting_event"

events_datafile = "data/events.csv"
rules_md = "data/rules.md"
event_participants = "data/participants.yaml"
users_table = "data/users.yaml"

results_path = "data/results/"


def get_votes_db(event_id: int):
    db = TinyDB(votes_db)
    table = db.table(str(event_id))
    # this call is required to setup the table in case it's empty (?)
    table.all()

    return table

# event = 0 in current_event file to disable voting and showing
# locked = 1 to disable changing votes
# eventually make it automatic depending on date
def get_current_voting_event():
    current_event = 0

    # with open("current_event", "r") as file:
    #     contents = file.read()
    #     current_event = int(contents.rstrip())

    with open(current_voting_event_statusfile, "r") as file:
        lines = [line.strip() for line in file.readlines()]
        current_event = int(lines[0])

    return current_event


def is_voting_open():
    open_status = 0
    with open(current_voting_event_statusfile, "r") as file:
        lines = [line.strip() for line in file.readlines()]
        open_status = int(lines[1])

    return open_status


def get_users_table():
    with open(users_table, 'r') as file:
        data = yaml.safe_load(file)
    return data['users']


def get_available_usernames():
    users = get_users_table()
    return list(users.keys())


def get_event_participants(event_id):
    with open(event_participants, 'r') as file:
        data = yaml.safe_load(file)

    return data[event_id]

