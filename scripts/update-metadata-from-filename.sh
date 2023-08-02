#!/bin/bash

path="$1"
[[ -z "$path" ]] && exit

echo "updating metadata of .flac files in $path"

# Enable nullglob to prevent the loop from executing when there are no matching files
shopt -s nullglob

# Iterate through all the FLAC files in the current directory
for flac_file in "$path"/*.flac; do
	echo "$flac_file"
	# Extract the artist and track name from the filename
	filename=$(basename "$flac_file")   # Get just the filename without the path
	artist_track="${filename%.flac}"    # Remove the ".flac" extension
	artist_name="${artist_track%% - *}" # Extract the artist name
	track_name="${artist_track#* - }"   # Extract the track name

	# Use metaflac to set the artist and track name in the FLAC file's metadata
	metaflac --set-tag="ARTIST=$artist_name" --set-tag="TITLE=$track_name" "$flac_file"
done

echo "done"
