#!/usr/bin/env python3

# NOTE a parallel service shell
#   History:
#     version 0.0: initial
#     version 0.1: removed external dependencies to local developer files
#     version 0.2: cleanup, published
#     version 0.3: cleaned up keyboard Ctrl-C handling
#     version 0.4: major cleanun and refactoring, introduces types

import os
import sys
import subprocess
import threading
import argparse

from functools import cmp_to_key
from typing import NoReturn
from collections import namedtuple

###############################################################################

ServiceResult = namedtuple("ServiceResult", "servicename output retval issysv")

g_addcols = False
g_debug_level = 0
g_verbose     = 0

###############################################################################

def AddCol(msg: str, col: str) -> str:
	assert isinstance(msg, str)
	assert isinstance(col, str)

	if g_addcols:
		Colors = namedtuple('Colors', "BLUE LBLUE RED LRED GREEN LGREEN YELLOW LYELLOW PURPLE LPURPLE CYAN LCYAN NOCOLOR")
		COLORS = Colors("\033[0;34m", "\033[1;34m", "\033[0;31m", "\033[1;31m", "\033[0;32m", "\033[1;32m", "\033[0;33m", "\033[1;33m", "\033[0;35m", "\033[1;35m", "\033[0;36m", "\033[1;36m", "\033[0m")

		c = ""
		match col:
			case "red":
				c = COLORS.RED
			case "lred":
				c = COLORS.LRED
			case "green":
				c = COLORS.GREEN
			case "lgreen":
				c = COLORS.LGREEN
			case "yellow":
				c =COLORS.YELLOW
			case "lyellow":
				c =COLORS.LYELLOW
			case "purple":
				c =COLORS.PURPLE
			case "lpurple":
				c =COLORS.LPURPLE
			case "cyan":
				c =COLORS.CYAN
			case _:
				raise ValueError(f"color '{col}' not defined")

		msg = c + msg + COLORS.NOCOLOR

	return msg

def PrintStdErr(msg: str, col: str) -> None:
	print(AddCol(msg, col), file=sys.stderr)

def ERR(msg: str) -> NoReturn:
	PrintStdErr(f"ERROR: {msg}", "lred")
	sys.exit(-1)

def WARN(msg: str) -> None:
	PrintStdErr(f"WARN: {msg}", "lyellow")

def DBG(msg: str, level: int=1) -> None:
	if level < g_debug_level:
		PrintStdErr(f"DBG: {msg}", "lpurple")

def InitFiles(initdir: str) -> list[str]:
	r : list[str] = []
	for f in os.listdir(initdir):
		if os.access(initdir + "/" + f, os.X_OK) and f[-1]!="~":
			r.append(f)
	return sorted(r)

def SysCallPrimitive(cmd: str, quiet=True, checkretval=False) -> tuple:
	try:
		o = subprocess.getstatusoutput(cmd)

		retval = o[0]
		output = o[1].split("\n")

		assert isinstance(retval, int)
		assert isinstance(output, list)

		for i in output:
			assert isinstance(i, str)

		if not quiet:
			print("> " + cmd + " => retval=" + str(retval))
			for i in output:
				assert isinstance(i, str)
				print("  " + i)

		if checkretval and retval!=0:
			ERR(f"encountered retval!=0 in SysCallPrimitive(cmd='{cmd}', ..) {o[1]}")

		return output, retval
	except Exception as ex:
		ERR(f"encountered unexpected exception SysCallPrimitive(cmd='{cmd}', ..), exception='{ex}'")
		return "", -1

def ServiceResultFactory(servicename: str, output: list[str], retval: int, issysv: bool) -> ServiceResult:
	assert len(servicename) > 0
	assert -256 <= retval <= 256 # NOTE: abitrary limits
	return ServiceResult(servicename, output, retval, issysv)

def ServiceVStatus(results : list[ServiceResult], index: int, servicename:str, servicemode: int, isthreaded: bool) -> None:

	assert isinstance(index, int) and index >= 0 or index == -1
	assert isinstance(servicename, str) and len(servicename) > 0
	assert isinstance(servicemode, int) and 0 <= servicemode <= 1
	assert isinstance(isthreaded, bool)

	prefix = "thread" if isthreaded else ""
	DBG(f"{prefix}[{index}], {servicename}, {servicemode}, {isthreaded}", 2)

	if servicemode == 0:
		cmd = "/etc/init.d/" + servicename + " status"
	elif servicemode == 1 :
		cmd = "service " + servicename + " status"
	else:
		ERR(f"unhandeled servicemode={servicemode}")

	output, retval = SysCallPrimitive(cmd)

	DBG(f"{prefix}[{index}]: result={retval}, done")

	assert isinstance(output, list)
	assert isinstance(retval, int) and retval >= -2, f"type of r expected to be int, but is is '{type(retval)}' with value '{retval}'"

	assert index <= len(results)
	assert results[index].servicename == "N/A"

	DBG(f"service={servicename} return value={retval} to be placed in index={index} for cmd={cmd}", 1)

	results[index] = ServiceResultFactory(servicename, output, retval, True)

def ServiceDStatus(filter_out: list[str], exitstatus: bool) -> list[ServiceResult]:

	def TrimWhite(s: str) -> str:
		r = ""
		w = True
		for i in s:
			if i in [" ", "\t"]:
				if not w:
					r += i
				w = True
			else:
				r += i
				w = False
		#print(f"s='{s}'\nr='{r}'")
		return r

	def FilterOutIrrelevantServices(s: str, filter_out: list[str]) -> bool:
		for i in filter_out:
			if s.find(i) == 0:
				return False
		return True

	cmd = "systemctl list-units --all --type=service --no-pager"
	output = SysCallPrimitive(cmd)
	assert isinstance(output, tuple) and len(output)==2

	o = output[0]
	r = output[1]

	assert isinstance(o, list)
	assert isinstance(r, int)

	results : list[ServiceResult] = []

	for i in o:
		assert isinstance(i, str)
		t = i.replace("\n","").strip()
		n = t.find(".service")
		if n > 0:
			servicename = t[:n]
			v = TrimWhite(t[n+8:])

			c = -1
			if v.find("loaded active exited") == 0:
				c = 0 if exitstatus else 1 # change from 1 to 0 if active but exited services should be marked as running
			elif v.find("loaded inactive exited") == 0:
				c = 3
			elif v.find("loaded active running") == 0:
				c = 0
			elif v.find("loaded inactive dead") == 0:
				c = 3
			elif v.find("not-found inactive dead") == 0:
				c = -2
			elif v.find("masked inactive dead") == 0:
				c = -2
			elif v.find("loaded failed") == 0:
				c = -2
			elif v.find("not-found failed") == 0:
				c = -2
			else:
				WARN(f"unexpected systemctl status '{v}'")

			DBG(f"servicename={(servicename+',').ljust(48)} c={c},  v={v}", 1)

			if c>=0 and FilterOutIrrelevantServices(servicename, filter_out):
				results.append( ServiceResultFactory(servicename, [t], c, False) )
		else:
			pass

	return results

def JoinServiceResults(results_sysv: list[ServiceResult], results_sysd: list[ServiceResult]) -> dict[str, list[ServiceResult]]:

	r: dict[str, list[ServiceResult]] = {}
	
	for ri in results_sysv:
		k = ri.servicename
		assert k not in r
		r[k] = [ri]
		
	for ri in results_sysd:
		k = ri.servicename
		if k in r:
			r[k].append(ri)
		else:
			r[k] = [ri]

	for k, v in r.items():
		assert len(v) <= 2, f"expected max two type of results, got {len(v)} for key '{k}'"
		if len(v) > 1:	
			DBG(f"service {k.ljust(48)} in both maps, return values={[rj.retval for rj in v]}")

	return r

def CompareServiceNames(x: str, y:str) -> bool:
	return x.lower() < y.lower()

def PrintServiceResultsSub(servicename: str, r: int, srv: int, maxlen: int) -> None:
		assert 0 <= srv <= 4

		s = f"[?{r}?]"
		match r:
			case 0:
				s = AddCol("+", "lgreen")
			case 1:
				s = AddCol("*", "green")
			case 2:
				s = AddCol("2", "lyellow")
			case 3:
				s = AddCol("-", "lred")
			case _:
				ERR(f"unhandled return mode for r={r}")
		s = f"[ {s} ]"
		
		match srv:
			case 0:
				printsrv = "sysv"		
			case 1:
				printsrv = "sysd"		
			case 2:
				printsrv = "sysv,sysd"		
			case 3:
				printsrv = "sysv"
				if g_verbose > 1:
					printsrv += ",ignored sysd"		
			case 4:
				printsrv = "sysd"
				if g_verbose > 1:
					printsrv += ",ignored sysv"		
			case _:
				ERR(f"unhandled srv mode {srv}")
		printsrv = " (" + printsrv + ")"	

		printservicename = servicename.ljust(maxlen if g_verbose > 0 else -1)
		msg = AddCol(printservicename, "green" if r==0 else "red")
		if g_verbose > 0:
			msg += AddCol(printsrv, "purple")
	
		print(f"{s} {msg}")

def PrintServiceResults(results: dict[str, list[ServiceResult]], printonlyrunning: bool, choosesysmode: int) -> None:
	assert isinstance(results, dict)
	assert isinstance(printonlyrunning, bool)
	assert 0 <= choosesysmode <= 2

	sorted_keys : list[str] = []

	for k in sorted(results.keys(), key=cmp_to_key(CompareServiceNames)):
	
		if printonlyrunning:
			toprint =  0 in [ri.retval for ri in results[k]]
		else:
			toprint = True
			
		if toprint:
			assert k not in sorted_keys
			sorted_keys.append(k)

	if len(sorted_keys) == 0:
		WARN("no services to print, non running?")
		return

	maxlens : list[int] = sorted([len(j) for j in sorted_keys])
	maxlen = maxlens[-1]
	if len(maxlens) > 1 and maxlen-maxlens[-2] > 8:
		# NOTE: just a single long line, ignore it and use then next-longest line
		maxlen = maxlens[-2]

	for k in sorted_keys:
		v = results[k]
		n = len(v)
		assert 1 <= n <= 2 
		
		for i in range(n):
			ri = v[i]
			
			assert k == ri.servicename
			assert (n == 1) or ((i==0 and ri.issysv) or (i==1 and not ri.issysv)), f"implicit sorting in sublist, sysv then sysd"
			
			srv = 0 if ri.issysv else 1
			
			DBG(f"i={i}, servicename='{ri.servicename}',  r={ri.retval}", 2)
			
			if i+1 < n:
				rj = v[i+1]
				if rj.servicename == ri.servicename:
					assert ri.issysv != rj.issysv
					assert ri.issysv and not rj.issysv

					retval_sysv = ri.retval
					retval_sysd = rj.retval 
					
					if retval_sysv == retval_sysd:
						DBG(f"i={i}: skipping print of service '{ri.servicename}' with similar return values {ri.retval}/{rj.retval} ", 2)
						srv = 2
					elif choosesysmode > 0:
						DBG(f"choosesysmode = {choosesysmode} for service {ri.servicename}:  {ri.issysv}/r={ri.retval} vs {rj.issysv}/r={rj.retval}", 2)
						if choosesysmode == 1:
							if g_verbose > 3:
								WARN(f"ignoring return value={retval_sysd} from sysd for service '{rj.servicename}' that disagree with sysv return value={retval_sysv}")
							srv = 3
						if choosesysmode == 2:
							if g_verbose > 3:
								WARN(f"ignoring return value={retval_sysv} from sysv for service '{ri.servicename}' that disagree with sysd return value={retval_sysd}")
							ri = rj
							srv = 4
					elif g_verbose > 2:
						WARN(f"services does not agree on return value of '{rj.servicename}, return values are {ri.retval}(sysv)/{rj.retval}(sysd)")

			PrintServiceResultsSub(ri.servicename, ri.retval, srv, maxlen)
	
			if srv >= 2:
				DBG(f"break srv={srv}", 4)
				break

###############################################################################

def main() -> None:

	initd = "/etc/init.d"
	parser = argparse.ArgumentParser()
	parser.add_argument("-v",  "--verbose",     default = 0,      action="count",      help="increase output verbosity, default=0\n")
	parser.add_argument("-c",  "--coloradd",    default = False,  action="store_true", help="add colors, default=False\n")
	parser.add_argument("-b",  "--both",        default = False,  action="store_true", help="show both sysv and systemd services, default=False\n")
	parser.add_argument("-sv", "--choosesysv",  default = False,  action="store_true", help="if services disagree, choose sysv return values default=False\n")
	parser.add_argument("-sd", "--choosesysd",  default = False,  action="store_true", help="if services disagree, choose sysd return value, default=False\n")
	parser.add_argument("-r",  "--runningonly", default = False,  action="store_true", help="only show running services, default=False\n")
	parser.add_argument("-x",  "--exitstatus",  default = False,  action="store_true", help="special exit status handling when service is 'active (exited)', default=False\n")
	parser.add_argument("-s",  "--systemctl",   default = False,  action="store_true", help="use 'systemctl' command instead of'service' directly, default=False\n")
	parser.add_argument("-f",  "--filter",      default = False,  action="store_true", help="ignore irrelevant services in  'systemctl' mode, default=False\n")
	parser.add_argument("-n",  "--nonthreaded", default = False,  action="store_true", help="do not use threading for speedup, default=False\n")
	parser.add_argument("-d",  "--debug",       default = False,  action="store_true", help="debug print default=False\n")
	parser.add_argument("--direct",             default = False,  action="store_true", help=f"call '{initd}' directly instead of using 'service'/'systemctl', default=False\n")
	parser.add_argument("--initdir",            default = initd,  type=str,            help=f"init dir to scan, default='{initd}'\n")
	args = parser.parse_args()

	global g_verbose, g_debug_level, g_addcols
		
	g_verbose     = args.verbose
	g_debug_level = args.debug
	g_addcols     = args.coloradd
	
	initdir       = args.initdir
	bothmode      = args.both
	servicemode   = 2 if args.systemctl else (1 if not args.direct else 0)
	filterout : list[str] = ["user@", "getty@", "user-runtime-dir@", "systemd-fsck@", "systemd-"] if args.filter else []

	if args.choosesysv and args.choosesysd:
		ERR("you can not specify both --choosesysv and --choosesysd")
	
	if args.choosesysd and not (args.systemctl or args.both):
		ERR("you can not specify --choosesysd when not also choosing --systemctl or --both")
	
	if args.choosesysv and args.systemctl and not args.both:
		ERR("you can not specify --choosesysv when also choosing --systemctl (and not choosing --both)")

	if args.direct and args.systemctl:
		WARN("you specified both --inintd and -systemctl, using -systemctl")

	if servicemode == 0:
		WARN(f"calling '{initd}' may not produce the right status for services")

	# Get sysv status..
	results_sysv : list[ServiceResult] = []
	threads : list[threading.Thread] = []
	
	if servicemode < 2 or bothmode:
		services = InitFiles(initdir)
		n        = len(services)
		subservicemode = 0 if args.direct else 1
		
		if n<=0:
			WARN(f"no files in init dir '{initdir}'")

		for i in range(n):
			results_sysv.append(ServiceResultFactory("N/A", [], -256, True))

			if args.nonthreaded:
				ServiceVStatus(                                   results_sysv, i, services[i], subservicemode , False)
			else:
				x = threading.Thread(target=ServiceVStatus, args=(results_sysv, i, services[i], subservicemode, True))
				threads.append(x)
				x.start()

	assert (args.nonthreaded and len(threads)==0) or len(threads)==len(results_sysv)

	# Get systemd status..
	results_sysd : list[ServiceResult] = []
	if servicemode>=2 or bothmode:
		results_sysd = ServiceDStatus(filterout, args.exitstatus)

	# Join all threads for sysv status..
	for x in threads:
		assert isinstance(x, threading.Thread)
		x.join()

	# Join sysv and sysd results if needed..
	results = JoinServiceResults(results_sysv, results_sysd)

	PrintServiceResults(results, args.runningonly, 1 if args.choosesysv else (2 if args.choosesysd else 0))

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt as _:
		ERR("interrupted by keyboard Ctld-C, aborted")
	except Exception as e:
		WARN(f"exception occured, '{e}' ({str(type(e)).replace('<class ','').replace('>','')})")
		raise e
