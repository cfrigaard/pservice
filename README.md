# pservice

A parallel service shell for Linux, making a `service --status-all` return
faster, by calling service status in parallel running threads.

# Usage

Simply call `pservice.py` instead of `service --status-all` 

```
> pservice.py
 [ + ]  acpid
 [ - ]  alsa-utils
 
 [..]
 
 [ + ]  udev
 [ + ]  ufw
 [ + ]  unattended-upgrades
 [ - ]  uuidd
 [ - ]  x11-common
```

or if `systemctl list-units --all --type=service` is your prefered service
monitor, using colors (not shown in the output below), and only showing running
services, `pservice` outputs in the same, simple form as the old shell-based
`service`

```
> ./pservice.py -c -s -r
 [ + ]  accounts-daemon
 [ + ]  acpid
 [ + ]  bluetooth

 [..]

 [ + ]  systemd-journald
 [ + ]  systemd-logind
 [ + ]  systemd-resolved
 [ + ]  systemd-timesyncd
 [ + ]  systemd-udevd
 [ + ]  udisks2
 [ + ]  unattended-upgrades
 [ + ]  upower
 [ + ]  user@1000
 [ + ]  wpa_supplicant
```

# Install

Simply put the file
```
pservice.py
```
somewhere in path, and call it with Python3. The header of the file is a
She-bang for a Python3 interpreter

```
#!/usr/bin/env python3
```
you could change this, or call the python file directly with a specific
interpreter ala

```
> /opt/anaconda-2024.02/bin/python3 ./pservice.py 
```
if needed.

# Speedup

Normal `service` is very slow, and typically (depending on the amount of
services you have running) takes one to several seconds.  Running in parallel
mode brings this down, to typically under a second (0.5 seconds or so).

Running `systemctl` is always faster than the old `service` and
will be done in less than a second (0.8 seconds on my system), and
`pservice` brings this down to around 0.1 seconds. 

The `systemctl` does not run in parallel mode, so the reason for the small
speedup is unknown.

For a particurlar, yet small set of installed services the timing may look
as (see function in `demo.sh`)

```
TIMING: (needs a tictoc timer)..
  timing for service --status-all:                                 1.32 secs
  timing for ./pservice.py -c:                                     0.47 secs
  timing for systemctl list-units --all --type=service --no-pager: 0.7 secs
  timing for ./pservice.py -s:                                     0.16 secs
```

# Using `init.d` or `systemd`

The classical daemon handler was 'sysvinit' (or SysV) with all the shell scripts
places in `/etc/init.d/'. This service handler is simple, yet slow, due to
the sequential handling of servicecall.

The modern deamon handler is the 'systemd', but the shell interface for the
`systemctl` is not as easy to remember and easy to interpret, as the
`service` shell command: normal operation could be to just get all services,
but you need to remember, make an alias, or a small script file for doing
this in the `systemd`-world.

## A note on `/etc/init.d' and `systemctl` differences

Running in `pservice` in normal mode (no 'i' or '-s' switches) simply scans
the `sysvinit` service dir

```
/etc/init.d/
```

for services and does a parallel 

```
/etc/init.d/<someservice> status
```

call to determine if the status of the service.  

Querying services via the systemd command

```
systemctl list-units --all --type=service
```

is not equal to the `service`s mode before, since there are differences in
the amount of services visible from the two subsystem.

## A note on active but exited services 

Furthermore, there may be subtle differences in calling `/etc/init.d/`
individual via

```
service --status-all
```

compared to running a status on an individual service. This is due to the
interpretation of the status of loaded, activated and then exited services,
that in `pservice` is reported as not running. You can change this behaviour
in `pservice.py' by changing `c = 1` to `c = 0` in the line

```
  if v.find("loaded active exited")==0:
  	c = 1 # change to 0 if active but exited services should be marked as running
```

In particular the `console-setup.sh` and the `keyboard-setup.sh` produce
different status when being called via `services` or `pservice.py` (see also
the function ShowDiffs in `demo.sh`)

```
service --status-all > status_service_all.txt
pservice             > status_pservice.txt

diff -dw status_service_all.txt status_pservice.txt
``` 

producing the output

````
8c8
<  [ - ]  console-setup.sh
---
>  [ + ]  console-setup.sh
18c18
<  [ - ]  keyboard-setup.sh
---
>  [ + ]  keyboard-setup.sh
```