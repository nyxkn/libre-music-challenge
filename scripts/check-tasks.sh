#!/bin/bash

################################################################################
# check if upload tasks are complete

check_tasks() {
    # Fetch current tasks and parse JSON
    tasks=$(ia tasks | jq '.[]')

    # Check if there are no tasks
    if [ -z "$tasks" ]; then
        echo "no currently running tasks."
		notify-send "ia upload tasks" "finished"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "duration:" $(date -u -d @$duration +'%Hh %Mm %Ss')
		exit
    else
        echo "..."
    fi
}

echo "checking if upload tasks have finished..."

start_time=$(date +%s)

while true; do
    check_tasks
    sleep 1m
done
