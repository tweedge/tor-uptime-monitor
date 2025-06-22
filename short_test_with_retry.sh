#!/bin/bash
max_retry=5
counter=0
until docker run -e TEST_CI='ON' --rm tweedge/tor-uptime-monitor:test
do
   sleep 1
   [[ counter -eq $max_retry ]] && echo "Ran out of retries!" && exit 1
   echo "Trying again. Try #$counter"
   ((counter++))
done
exit 0