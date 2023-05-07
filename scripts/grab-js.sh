#!/bin/sh

this_dir="$(dirname $(realpath $0))"

cd "$this_dir/../static/src"
wget -N https://unpkg.com/htmx.org/dist/htmx.min.js
