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
monitor, using colors, and only showing running services

```
> ./pservice.py -c -s -r
 [ + ]  accounts-daemon
 [ + ]  acpid
 [ + ]  bluetooth
 [ + ]  cron
 [ + ]  dbus
 [ + ]  fwupd
 [ + ]  getty@tty1
 [ + ]  irqbalance
 [ + ]  lightdm
 [ + ]  networkd-dispatcher
 [ + ]  NetworkManager
 [ + ]  polkit
 [ + ]  rtkit-daemon
 [ + ]  systemd-journald
 [ + ]  systemd-logind
 [ + ]  systemd-resolved
 [ + ]  systemd-timesyncd
 [ + ]  systemd-udevd
 [ + ]  udisks2
 [ + ]  unattended-upgrades
 [ + ]  upower
 [ + ]  user@1000
 [ + ]  vpnagentd
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

Running `systemctl` is normally somewhat faster than the old `service` and
will be done in a second or little less than a second, and `pservice` brings
this down to around 0.1 seconds. 

# A note on `/etc/init.d' and `systemctl`

Running in `service --status-all` mode simply scans the service dir

```
	/etc/init.d
```

for services and does a parallel 

```
	/etc/init.d/<someservice> status
```
call to determine if the status of the service. This is the `old-fashion`
servicemode now to be phased out with `systemctl`.

Querying services via the systemd command

```
	systemctl list-units --all --type=service
```
is not equal to the `service`s mode before, since there are differences in
the amount of services visible from the two subsystem.

Furthermore, there may be subtle differences in calling `/etc/init.d/`
individual via

```
	service --status-all
```

compared to running a status on an individual service.
