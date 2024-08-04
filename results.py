#!/usr/bin/env python3

from collections import defaultdict
import sys
import statistics
import pandas as pd
import numpy
import common as c
import copy
import os
import json


users_table_cached = {}

check_only = False


def username_to_artist(username):
    return users_table_cached[username]


def artist_to_username(artist):
    # swap key/value
    # reverse_dict = {v:k for k,v in users_table_cached.items()}
    reverse_dict = dict((v,k) for k,v in users_table_cached.items())
    return reverse_dict[artist]


def main():
    # Check if at least one command-line argument is provided
    if len(sys.argv) < 2:
        print("Please provide the event id.")
        sys.exit(1)

    args = sys.argv[1:]
    arg_event = int(args[0])

    global check_only
    if len(args) > 1:
        if args[1] == "check":
            check_only = True

    current_event = c.get_current_voting_event()
    if arg_event > current_event or arg_event < 18:
        print("We don't have the data for this event.")
        sys.exit(1)

    global users_table_cached
    users_table_cached = c.get_users_table()

    generate_results(arg_event)



def rename_dict_key(dictionary, old_key, new_key):
    if old_key == new_key:
        return

    if old_key in dictionary:
        dictionary[new_key] = dictionary[old_key]
        del dictionary[old_key]


def generate_results(event_id):
    db = c.get_votes_db(event_id)

    # participating_usernames = c.get_event_participants(event_id)

    # convert participating artists to usernames
    participating_artists = c.get_event_participants(event_id)
    participating_usernames = []
    for artist in participating_artists:
        participating_usernames.append(artist_to_username(artist))


    self_votes = {}

    votes_received = defaultdict(list)
    votes_given = defaultdict(list)

    # rename all artist names to usernames
    user_entries_orig = db.all()
    user_entries = copy.deepcopy(user_entries_orig)
    for i in range(len(user_entries_orig)):
        entry = user_entries_orig[i]
        for to_artist in entry["votes"]:
            to_user = artist_to_username(to_artist)
            rename_dict_key(user_entries[i]["votes"], to_artist, to_user)


    for user_entry in user_entries:
        from_user = user_entry["user"]

        # sort votes by to_artist
        votes_from_user = dict(sorted(user_entry["votes"].items()))

        for to_user,vote in votes_from_user.items():
            votes_received[to_user].append(int(vote))
            votes_given[from_user].append(int(vote))


    # missing_votes = False
    missing_votes_by_users = []
    for user in participating_usernames:
        if not user in votes_given or len(votes_given[user]) < len(participating_usernames):
            print(f"user {user} has not completed the voting")
            # missing_votes = True
            missing_votes_by_users.append(user)

    for user,votes in votes_given.items():
        if not user in participating_usernames and len(votes) < len(participating_artists):
            print(f"non-participant {user} has started but not completed the voting")
            # missing_votes = True

    if missing_votes_by_users:
        print(f"=== votes are still missing by users: {missing_votes_by_users} ===")
        answer = input("continue anyway? (missing users will be disqualified) (y/N)")
        if answer != "y":
            exit()
        print("=== continuing ===")
    else:
        print("=== all votes are present! continuing ===")

    if check_only:
        exit()
    else:
        print("=== generating results... ===")

    for missing_user in missing_votes_by_users:
        votes_given[missing_user] = [-1] * len(participating_usernames)
        self_votes[missing_user] = -1

    for user_entry in user_entries:
        from_user = user_entry["user"]

        if from_user in participating_usernames:
            # if we have a self vote, store it
            if from_user in user_entry["votes"]:
                self_votes[from_user] = int(user_entry["votes"][from_user])
            else:
                self_votes[from_user] = numpy.nan
            # change the vote to 0 for further calculations
            # self votes are now stored independently in self_votes
            user_entry["votes"][from_user] = '0'


    def my_sort(tuple):
        user = tuple[0]
        # sort participating users first, non-participating last
        # then by name
        return (not user in participating_usernames, user)

    # sort by from_user
    votes_given = dict(sorted(votes_given.items(), key=my_sort))
    self_votes = dict(sorted(self_votes.items()))

    votes_matrix_given = list(votes_given.values())
    votes_matrix_received = numpy.transpose(votes_matrix_given)

    # ========================================
    # calculate votes distribution

    votes_distribution = {}
    for i in range(5, 0, -1):
        votes_distribution[i] = {'count': 0, '%': 0}

    for votes in votes_matrix_given:
        for vote in votes:
            if vote <= 0:
                continue
            votes_distribution[vote]['count'] += 1

    total_votes = 0
    for vote,values in votes_distribution.items():
        total_votes += values['count']

    for vote,values in votes_distribution.items():
        values['%'] = round(values['count'] / total_votes * 100, 1)

    # ========================================
    # calculate generosity

    generosity_stats = {}

    for user,votes in votes_given.items():
        generosity_stats[user] = {}
        len_votes = len(votes)
        if user in participating_usernames:
            # one of the votes is own-vote so 0, so we skip that
            len_votes -= 1
        generosity_stats[user]['given'] = round(sum(votes) / len_votes, 1)

    generosity_sum = 0
    for k,v in generosity_stats.items():
        generosity_sum += v['given']

    avg_generosity = generosity_sum / len(generosity_stats.keys())

    for user,stats in generosity_stats.items():
        stats['generosity'] = round((stats['given'] - avg_generosity) / avg_generosity * 100, 1)

    # ========================================
    # gather participant votes and calculate averages

    participant_stats = {}

    for user,votes in votes_received.items():
        votes_sum = sum(votes)
        avg = statistics.mean(filter(lambda x: x > 0, votes))
        avg = round(avg, 1)
        participant_stats[user] = {
            'score': votes_sum,
            'average': avg,
        }
        for v in range(5, 0, -1):
            participant_stats[user][str(v) + "s"] = len(list(filter(lambda n: n == v, votes)))

    def score_sort(item):
        if user in missing_votes_by_users:
            # if disqualified return large value to ensure it's ordered last
            return (float('inf'),)

        return (item[1]["score"],
                item[1]["5s"],
                item[1]["4s"],
                item[1]["3s"],
                item[1]["2s"])

    participant_stats_ordered = dict(sorted(participant_stats.items(), key=score_sort, reverse=True))

    # ========================================
    # generate scoreboard

    scoreboard = {}
    user_stats = []
    counter = 1
    for user,stats in participant_stats_ordered.items():
        entry = {}
        entry["name"] = username_to_artist(user)
        if user in missing_votes_by_users:
            entry["placement"] = "DQ"
        else:
            entry["placement"] = counter
            counter += 1
        # this appends stats dict to our entry dict
        entry.update(stats.copy())
        user_stats.append(entry)

    for entry in user_stats:
        scoreboard[entry["placement"]] = entry


    # ========================================
    # generate json file
    # Specify the file name

    json_filename = f"{c.results_path}/lmc{event_id}-scoreboard.json"

    # Write the dictionary to a file
    with open(json_filename, 'w') as json_file:
        # scoreboard_copy = copy.deepcopy(scoreboard)
        # for rank in list(scoreboard.keys()):
        #     if artist_to_username(scoreboard[rank]["name"]) in missing_votes_by_users:
        #         print(f"delete {scoreboard[rank]}")
        #         del scoreboard[rank]
            
        json.dump(scoreboard, json_file, indent=4)

    # ========================================
    # generate ods file

    scoreboard_df = pd.DataFrame.from_dict(scoreboard, orient='index')
    generosity_df = pd.DataFrame.from_dict(generosity_stats, orient='index')
    votes_distribution_df = pd.DataFrame.from_dict(votes_distribution, orient='index')

    votes_given_chart_df = pd.DataFrame.from_dict(votes_given, orient='index')
    votes_given_chart_df.columns = sorted(participating_usernames)
    votes_given_chart_df = votes_given_chart_df.replace(0, numpy.nan)
    votes_given_chart_df = votes_given_chart_df.replace(-1, numpy.nan)

    votes_given_chart_df.loc['total score',:] = votes_given_chart_df.sum(axis=0, skipna=True)
    # the iloc slice [:-1] selects all rows except last
    votes_given_chart_df.loc[:,'total given'] = votes_given_chart_df.iloc[:-1].sum(axis=1)
    # to only show total given for participating users:
    # votes_given_chart_df.loc[:,'total given'] = votes_given_chart_df.iloc[:len(participating_usernames)].sum(axis=1)

    votes_given_chart_df.loc[''] = pd.Series([None] * len(votes_given_chart_df.columns))

    # average of participant columns (all minus the last one)
    # for participant rows (all minus last two we just added)
    # this would calculate the average again. but we already have that, so just use that
    # votes_given_chart_df.loc['average',:] = votes_given_chart_df.iloc[:-2, :-1].mean(axis=0, skipna=True)
    avgs_list = []
    for k,v in participant_stats.items():
        avgs_list.append(v['average'])
    votes_given_chart_df.loc['average',:] = avgs_list + [numpy.nan]

    # when setting the row, we need to add an extra value to match the total row length
    votes_given_chart_df.loc['self vote',:] = list(self_votes.values()) + [numpy.nan]

    notes = {'notes': [
        "this spreadsheet was automatically generated with this script:",
        "https://github.com/nyxkn/libre-music-challenge/blob/main/results.py",
        "",
        "generosity",
        "a generosity of 0 is the average generosity",
        "positive/negative values show how much more/less generous than the average the voting was"
    ]}
    notes_df = pd.DataFrame(notes)


    filename = f"{c.results_path}/lmc{event_id}-results.ods"

    if os.path.exists(filename):
        answer = input(f"{filename} already exists! overwrite? (y/N)")
        if answer != "y":
            exit()

    # excelwriter has an issue with python linters. ignore this error
    # the pylint comment doesn't seem to work. are we even using pylint?
    with pd.ExcelWriter(f"{c.results_path}/lmc{event_id}-results.ods", mode="w", engine="odf") as writer: #pylint: disable=abstract-class-instantiated
        scoreboard_df.to_excel(writer, sheet_name="scoreboard")
        votes_given_chart_df.to_excel(writer, sheet_name="votes")
        generosity_df.to_excel(writer, sheet_name="generosity")
        votes_distribution_df.to_excel(writer, sheet_name="distribution")
        notes_df.to_excel(writer, sheet_name="notes", header=False, index=False)


if __name__ == "__main__":
    main()
