#!/bin/bash

function Timing()
{
	echo -n "  timing for $@: "
	tictoc.py -x
	$@ >/dev/null
	tictoc.py
}

function ShowTimings()
{
	which tictoc.py
	if [ $? == 0 ]; then
		echo "TIMING: (needs a tictoc timer).."
		Timing service --status-all
		Timing ./pservice.py -c
		Timing systemctl list-units --all --type=service --no-pager
		Timing ./pservice.py -s
	fi
}

function ShowDiffs()
{
	echo "DEMO: diff to running service.."

	service --status-all > service_status_all.txt
	pservice             > pservice_status_all.txt

	diff -dw service_status_all.txt pservice_status_all.txt
}

function ShowConsoleStatus()
{
	service console-setup status
	echo "STATUS: service console-setup status=$?"
	systemctl status console-setup
	echo "STATUS: systemctl status console-setup=$?"
}

function Demos()
{

	echo "DEMO: pservice demo, normal operation.."

	pservice.py

	echo "with colors.."

	pservice.py -c

	echo "DEMO: using systemctl instead of /etc/init.d/ .."

	pservice.py -c -s

	echo "DEMO: and showing only running services.."

	pservice.py -c -s -r

}

Demos
#ShowTimings
#ShowDiffs
#ShowConsoleStatus