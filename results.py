#!/usr/bin/env python3

from collections import defaultdict
import sys
import statistics
import pandas as pd
import numpy
import common as c


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
    for user_entry in db:
        # user who has given the votes. this uses username for user and artistname for given votes
        if user_entry["user"] in participating_usernames:
            from_user = user_entry["user"]
            from_artist = username_to_artist(from_user)

            if from_artist in user_entry["votes"]:
                self_votes[from_artist] = int(user_entry["votes"][from_artist])
            else:
                self_votes[from_artist] = numpy.nan
            user_entry["votes"][from_artist] = '0'

            # sort votes by to_artist
            votes_from_user = dict(sorted(user_entry["votes"].items()))
            for to_artist,vote in votes_from_user.items():
                    votes_received[to_artist].append(int(vote))
                    votes_given[from_artist].append(int(vote))


    # sort by from_user
    votes_given = dict(sorted(votes_given.items()))
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

    for artist,votes in votes_given.items():
        generosity_stats[artist] = {}
        generosity_stats[artist]['given'] = sum(votes)

    generosity_sum = 0
    for k,v in generosity_stats.items():
        generosity_sum += v['given']

    avg_generosity = generosity_sum / len(generosity_stats.keys())

    for artist,stats in generosity_stats.items():
        stats['generosity'] = round((stats['given'] - avg_generosity) / avg_generosity * 100, 1)

    # ========================================
    # gather participant votes statistics

    participant_stats = {}

    for artist,votes in votes_received.items():
        votes_sum = sum(votes)
        avg = statistics.mean(filter(lambda x: x != 0, votes))
        participant_stats[artist] = {
            'score': votes_sum,
            'average': avg,
        }
        for v in range(5, 0, -1):
            participant_stats[artist][str(v) + "s"] = len(list(filter(lambda n: n == v, votes)))

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
    for artist,stats in participant_stats_ordered.items():
        entry = {}
        entry["name"] = artist
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
    votes_given_chart_df.columns = sorted(participating_artists)
    votes_given_chart_df = votes_given_chart_df.replace(0, numpy.nan)

    votes_given_chart_df.loc['total score',:] = votes_given_chart_df.sum(axis=0, skipna=True)
    # the iloc slice [:-1] selects all rows except last
    votes_given_chart_df.loc[:,'total given'] = votes_given_chart_df.iloc[:-1].sum(axis=1)

    votes_given_chart_df.loc[''] = pd.Series([None] * len(votes_given_chart_df.columns))

    # average of participant columns (all minus the last one)
    # for participant rows (all minus last two we just added)
    votes_given_chart_df.loc['average',:] = votes_given_chart_df.iloc[:-2, :-1].mean(axis=0, skipna=True)
    # when setting the row, we need to add an extra value to match the total row length
    votes_given_chart_df.loc['self vote',:] = list(self_votes.values()) + [numpy.nan]

    notes = {'notes': [
        "this spreadsheet was automatically generated with this script:",
        "https://github.com/nyxkn/libre-music-challenge/blob/main/results.py",
    ]}
    notes_df = pd.DataFrame(notes)

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
