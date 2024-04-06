#!/bin/bash

id="$1"
title="$2"
date="$3"
lm_link="$4"
description="Submissions for the Libre Music Challenge #$id: \"$title\", $date.

More info about the challenge at: https://linuxmusicians.com/viewtopic.php?t=$lm_link
"

echo "id: $id"
echo "title: $title"
echo "date: $date"
echo "lm_link: $lm_link"
echo "desc: $description"

read -p "continue? (y/N) " -n1 prompt_answer && echo ""
[[ "$prompt_answer" != "y" ]] && exit

echo
echo "uploading .flac files"

# setup the item with flac files
ia upload "libre-music-challenge-$id" ./*.flac \
	--metadata="title:Libre Music Challenge #$id" \
	--metadata="mediatype:audio" \
	--metadata="collection:opensource_audio" \
	--metadata="subject:libre music challenge" \
	--metadata="licenseurl:https://creativecommons.org/licenses/by-sa/4.0/" \
	--metadata="description:$description"

echo
echo "uploading .ogg files"
# add ogg if any
ia upload "libre-music-challenge-$id" ./*.ogg

# add source
# echo
# echo "uploading source files"
# ia upload "libre-music-challenge-$id" ./source

echo
echo "waiting to check tasks..."
sleep 1m

check-tasks.sh
