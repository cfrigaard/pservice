#!/bin/bash

echo "DEMO: pservice demo, normal operation.."

pservice.py

echo "with colors.."

pservice.py -c

echo "DEMO: using systemctl instead of /etc/init.d/ .."

pservice.py -c -s

echo "DEMO: and showing only running services.."

pservice.py -c -s -r

function Timing()
{
	echo -n "  timing for $@: "
	tictoc.py -x
	$@ >/dev/null
	tictoc.py 
}
	
which tictoc.py
if [ $? == 0 ]; then
	echo "TIMING: (needs a tictoc timer).."
	Timing service --status-all
	Timing ./pservice.py -c 
	Timing systemctl list-units --all --type=service --no-pager
	Timing ./pservice.py -s
fi
