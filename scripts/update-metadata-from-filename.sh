#!/bin/bash

path="$1"
[[ -z "$path" ]] && exit

# Change to the directory
cd "$path" || exit 1

echo "updating metadata of .flac and .ogg files in $path"

# Enable nullglob to prevent the loop from executing when there are no matching files
shopt -s nullglob

# Iterate through all the FLAC files in the current directory
for file in *.flac *.ogg; do
	echo "$file"

	# Extract the artist and track name from the filename
	filename=$(basename "$file")   # Get just the filename without the path
	# full_name="${filename%.flac}"    # Remove the ".flac" extension
	full_name="${filename%.*}"    # Remove the file extension
	artist_name="${full_name%% - *}" # Extract the artist name
	track_name="${full_name#* - }"   # Extract the track name

    # Check the file extension
    if [[ $file == *.flac ]]; then
		# remove existing tags (otherwise --set-tag just adds a second one)
		metaflac --remove-tag="ARTIST" --remove-tag="TITLE" "$file"
		# Use metaflac to set the artist and track name in the FLAC file's metadata
		metaflac --set-tag="ARTIST=$artist_name" --set-tag="TITLE=$track_name" "$file"
    elif [[ $file == *.ogg ]]; then
		tmpfile=$(mktemp)
		# vorbiscomment -l "$file"
		# Export existing tags to a file
		vorbiscomment -e -l "$file" > "$tmpfile"
		# vorbiscomment -w -t "ARTIST=$artist_name" -t "TITLE=$track_name" "$file"
		# Modify the artist and title tags
		sed -i "/^ARTIST=/c\ARTIST=$artist_name" "$tmpfile"
		sed -i "/^TITLE=/c\TITLE=$track_name" "$tmpfile"
		# Import tags back from the file
		vorbiscomment -w -c "$tmpfile" "$file"
		rm "$tmpfile"
    fi

done

echo "done"
