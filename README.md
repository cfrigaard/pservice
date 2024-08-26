# pservice

A parallel service shell for Linux, making a `service --status-all` return
faster, by calling service status in parallel running threads.

# Usage

Simply call `pservice.py` instead of `service --status-all` 

```
> pservice.py
 [ x ]  apparmor
 [ + ]  bluetooth
 [ x ]  console-setup.sh
 [ + ]  cron
 [ + ]  dbus
 [ x ]  keyboard-setup.sh
 [ x ]  kmod
 [ + ]  lightdm
 [ x ]  lm-sensors
 [ x ]  plymouth-log
 [ x ]  procps
 [ x ]  ufw
 [ + ]  unattended-upgrades
 [ x ]  virtualbox
```

or if `systemctl list-units --all --type=service` is your prefered service
monitor, using colors (not shown in the output below), and only showing running
services, `pservice` outputs in the same, simple form as the old shell-based
`service`

```
> ./pservice.py -s 
 [ x ]  apparmor
 [ + ]  bluetooth
 [ x ]  console-setup.sh
 
 ..
 
 [ + ]  systemd-journald
 [ + ]  systemd-logind
 [ + ]  systemd-machined
 [ x ]  systemd-modules-load
 [ x ]  systemd-random-seed
 [ x ]  systemd-remount-fs
 [ + ]  systemd-resolved
 
 ..

 [ + ]  thermald
 [ + ]  udisks2
 [ x ]  ufw
 [ + ]  unattended-upgrades
 [ + ]  upower
 [ + ]  wpa_supplicant
```

Join both systemctl and '/etc/init.d/' services (`-b`), and filter-out active but
exited services (`-x`), and also remove the large amount of internal systemd
services (`-f`)

```
> ./pservice.py -b -f -x -v 
 [ + ]  bluetooth           (sysv,sysd)
 [ + ]  cron                (sysv,sysd)
 [ + ]  dbus                (sysv,sysd)
 [ + ]  lightdm             (sysv,sysd)
 [ + ]  NetworkManager      (sysd)
 [ + ]  polkit              (sysd)
 [ + ]  snapd               (sysd)
 [ + ]  thermald            (sysd)
 [ + ]  udisks2             (sysd)
 [ + ]  unattended-upgrades (sysv,sysd)
 [ + ]  upower              (sysd)
 [ + ]  virtlockd           (sysd)
 [ + ]  virtlogd            (sysd)
 [ + ]  vpnagentd           (sysd)
 [ + ]  wpa_supplicant      (sysd)
```
here shown without colors.

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
placed in `/etc/init.d/'. This service handler is simple, yet slow, due to
the sequential handling of servicecall.

The modern deamon handler is the 'systemd', but the shell interface for the
`systemctl` is not as easy to remember and easy to interpret, as the
`service` shell command: normal operation is to get all services, but you
need to remember, make an alias, or a small script file for doing this in
the `systemd`-world.

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

There is a difference commando in the file 'demo.sh' that essentially just
do a diff on the two service-subsystems 

```
service --status-all > status_service_all.txt
pservice.py -a -nc    > status_pservice.txt

diff -dw status_service_all.txt status_pservice.txt
``` 

that for my currently running system producing the output

````
<  [ + ]  alsa-utils
---
>  [ - ]  alsa-utils
4c4
<  [ + ]  apparmor
---
>  [ x ]  apparmor
6c6
<  [ - ]  console-setup.sh
---
>  [ x ]  console-setup.sh
11,12c11,12
<  [ - ]  keyboard-setup.sh
<  [ + ]  kmod
---
>  [ x ]  keyboard-setup.sh
>  [ x ]  kmod
...

```
