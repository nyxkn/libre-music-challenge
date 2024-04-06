#!/bin/bash

path="$1"
[[ -z "$path" ]] && echo "need path" && exit

echo "renaming files in $path"

# Navigate to the folder
cd "$path" || exit

# Loop through all files in the folder
for file in *; do
	# Check if the file is a regular file
	if [ -f "$file" ]; then
		# Replace underscores with spaces
		new_name="${file//_/ }"

		# Replace hyphens between words with ' - '
		# new_name=$(echo "$new_name" | sed 's/\([a-zA-Z0-9]\)-\([a-zA-Z0-9]\)/\1 - \2/g')

		# Rename the file
		if [ "$file" != "$new_name" ]; then
			mv "$file" "$new_name"
			echo "Renamed: $file -> $new_name"
		fi

	fi
done

echo
echo "artists:"

for file in *; do
    if [[ $file == *' - '* ]]; then
        # Extract the artist name by cutting the string before ' - '
        artist=${file%% - *}

        # Print the artist name
        echo "- $artist"
    fi
done

echo
echo "rename process complete."
