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
	which tictoc.py >/dev/null 2>/dev/null
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

	service --status-all > status_service_all.txt
	pservice             > status_pservice.txt
	echo "Diff status_service_all.txt status_pservice.txt.."
	diff -dw status_service_all.txt status_pservice.txt

	pservice             > status_initd_direct.txt
	echo "Diff status_service_all.txt status_initd_direct.txt.."
	diff -dw status_service_all.txt status_initd_direct.txt
}

function ShowConsoleStatus()
{
	service console-setup.sh status
	echo "STATUS: servics console-setup.sh status=$?"
	/etc/init.d/console-setup.sh status
	echo "STATUS: /etc/init.d/console-setup.sh status=$?"
	systemctl status console-setup
	echo "STATUS: systemctl status console-setup=$?"
}

function Demos()
{
	echo "DEMO: pservice demo, normal operation.."

	pservice.py

	echo "with no colors only using systemctl"

	pservice.py -nc -s

	echo "DEMO: using systemctl instead of /etc/init.d/ .."

	pservice.py -s

	echo "DEMO: and showing only running services.."

	pservice.py -s -x

	echo "DEMO: showing all services for both /etc/init.d/ and systemctl.."

	pservice.py -a
}

Demos

#ShowTimings
#ShowDiffs
#ShowConsoleStatus