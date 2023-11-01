#!/bin/bash

path="$1"
[[ -z "$path" ]] && exit

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

echo "Rename process complete."
