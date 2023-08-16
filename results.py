#!/usr/bin/env python3

from collections import defaultdict
import sys
import statistics
import pandas as pd
import numpy
import common as c
import copy
import os


users_table_cached = {}

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
        print("Please provide a command-line argument.")
        sys.exit(1)

    # Read the first command-line argument
    arg = int(sys.argv[1])

    current_event = c.get_current_event()
    if arg > current_event or arg < 18:
        print("We don't have the data for this event.")
        sys.exit(1)

    global users_table_cached
    users_table_cached = c.get_users_table()

    generate_results(arg)



def rename_dict_key(dictionary, old_key, new_key):
    if old_key in dictionary:
        dictionary[new_key] = dictionary[old_key]
        del dictionary[old_key]


def generate_results(event_id):
    db = c.get_votes_db(event_id)

    # always use artist name instead of username

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

        if from_user in participating_usernames:
            # user who has given the votes

            # if we have a self vote, store it
            if from_user in user_entry["votes"]:
                self_votes[from_user] = int(user_entry["votes"][from_user])
            else:
                self_votes[from_user] = numpy.nan
            user_entry["votes"][from_user] = '0'

        # sort votes by to_artist
        votes_from_user = dict(sorted(user_entry["votes"].items()))
        for to_user,vote in votes_from_user.items():
            votes_received[to_user].append(int(vote))
            votes_given[from_user].append(int(vote))

    missing_votes = False
    for user in participating_usernames:
        if not user in votes_given or len(votes_given[user]) < len(participating_usernames):
            print(f"user {user} has not completed the voting")
            missing_votes = True

    for user,votes in votes_given.items():
        if not user in participating_usernames and len(votes) < len(participating_artists):
            print(f"non-participant {user} has started but not completed the voting")
            missing_votes = True

    if missing_votes:
        print("=== votes are still missing. exiting. ===")
        exit()


    def my_sort(tuple):
        user = tuple[0]
        # sort participating users first, non-participating last
        # then by name
        return (not user in participating_usernames, user)

    # sort by from_user
    votes_given = dict(sorted(votes_given.items(), key=my_sort))
    self_votes = dict(sorted(self_votes.items()))

    # votes matrixes. currently not being used
    votes_matrix_given = list(votes_given.values())
    votes_matrix_received = numpy.transpose(votes_matrix_given)

    # ========================================
    # calculate votes distribution

    votes_distribution = {}
    for i in range(5, 0, -1):
        votes_distribution[i] = {'count': 0, '%': 0}

    for votes in votes_matrix_given:
        for vote in votes:
            if vote == 0:
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
        generosity_stats[user]['given'] = sum(votes)

    generosity_sum = 0
    for k,v in generosity_stats.items():
        generosity_sum += v['given']

    avg_generosity = generosity_sum / len(generosity_stats.keys())

    for user,stats in generosity_stats.items():
        stats['generosity'] = round((stats['given'] - avg_generosity) / avg_generosity * 100, 1)

    # ========================================
    # gather participant votes statistics

    participant_stats = {}

    for user,votes in votes_received.items():
        votes_sum = sum(votes)
        avg = statistics.mean(filter(lambda x: x != 0, votes))
        avg = round(avg, 1)
        participant_stats[user] = {
            'score': votes_sum,
            'average': avg,
        }
        for v in range(5, 0, -1):
            participant_stats[user][str(v) + "s"] = len(list(filter(lambda n: n == v, votes)))

    def score_sort(item):
        return (item[1]["score"],
                item[1]["5s"],
                item[1]["4s"],
                item[1]["3s"],
                item[1]["2s"])

    participant_stats_ordered = dict(sorted(participant_stats.items(), key=score_sort, reverse=True))

    # ========================================
    # generate scoreboard

    scoreboard = {}
    counter = 1
    for user,stats in participant_stats_ordered.items():
        entry = {}
        entry["name"] = username_to_artist(user)
        # this appends stats dict to our entry dict
        entry.update(stats.copy())
        scoreboard[counter] = entry
        counter += 1

    # ========================================
    # generate ods file

    scoreboard_df = pd.DataFrame.from_dict(scoreboard, orient='index')
    generosity_df = pd.DataFrame.from_dict(generosity_stats, orient='index')
    votes_distribution_df = pd.DataFrame.from_dict(votes_distribution, orient='index')

    votes_given_chart_df = pd.DataFrame.from_dict(votes_given, orient='index')
    votes_given_chart_df.columns = sorted(participating_usernames)
    votes_given_chart_df = votes_given_chart_df.replace(0, numpy.nan)

    votes_given_chart_df.loc['total score',:] = votes_given_chart_df.sum(axis=0, skipna=True)
    # the iloc slice [:-1] selects all rows except last
    votes_given_chart_df.loc[:,'total given'] = votes_given_chart_df.iloc[:-1].sum(axis=1)

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
        print(f"{filename} already exists!")
        exit()
    else:
        # excelwriter has an issue with linters. ignore this error
        # the pylint comment doesn't seem to work. are we even using pylint?
        with pd.ExcelWriter(f"{c.results_path}/lmc{event_id}-results.ods", mode="w", engine="odf") as writer: #pylint: disable=abstract-class-instantiated
            scoreboard_df.to_excel(writer, sheet_name="scoreboard")
            votes_given_chart_df.to_excel(writer, sheet_name="votes")
            generosity_df.to_excel(writer, sheet_name="generosity")
            votes_distribution_df.to_excel(writer, sheet_name="distribution")
            notes_df.to_excel(writer, sheet_name="notes", header=False, index=False)


if __name__ == "__main__":
    main()
