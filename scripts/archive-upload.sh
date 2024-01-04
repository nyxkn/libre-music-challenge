#!/bin/bash

id="$1"
title="$2"
date="$3"
lm_link="$4"
description="Submissions for the Libre Music Challenge #$id: \"$title\", $date.

More info about the challenge at: https://linuxmusicians.com/viewtopic.php?t=$lm_link
"

echo "$id"
echo "$title"
echo "$date"
echo "$lm_link"
echo "$description"

read -p "Continue? (y/N): " r
r=${r:-n}
[[ $r != "y" ]] && exit

ia upload "libre-music-challenge-$id" ./*.flac ./*.ogg \
	--metadata="title:Libre Music Challenge #$id" \
	--metadata="mediatype:audio" \
	--metadata="collection:opensource_audio" \
	--metadata="subject:libre music challenge" \
	--metadata="licenseurl:https://creativecommons.org/licenses/by-sa/4.0/" \
	--metadata="description:$description"
