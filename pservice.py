#!/usr/bin/env python3

# NOTE a parallel service shell
#   History:
#     version 0.0: initial
#     version 0.1: removed external dependencies to local developer files
#     version 0.2: cleanup, published
#     version 0.3: cleaned up keyboard Ctrl-C handling
#     version 0.4: major cleanun and refactoring, introduces types
#     version 0.5: moved all filtering to FilterServiceResults, elaboreated on 'acive (exited)' status
#     version 0.7: more cleanup, created _RESULT_STATUS map and remapped service retval

import os
import sys
import subprocess
import threading
import argparse

#from functools import cmp_to_key
from collections import namedtuple
from typing import Any, Mapping, NoReturn, Sequence # Iterable,  MutableMapping

###############################################################################

ServiceResult = namedtuple("ServiceResult", "servicename output retval issysv")

g_addcols = False
g_debug_level = 0
g_verbose     = 0

_RESULT_STATUS : dict[int,str] = {
		 0: "loaded active running",
		 1: "loaded active exited",
		-2: "loaded inactive exited",
		-3: "loaded inactive dead",
		-4: "not-found inactive dead",
		-5: "masked inactive dead",
		-6: "loaded failed",
		-7: "not-found failed",
		-8: "sysv inactive/failed",
		-1: "N/A", 
	}

###############################################################################


def isInstance(var: Any, expected_type: Any) -> bool:
	if not isinstance(var, expected_type):
		WARN(f"expected var '{var}' to be a '{type(expected_type)}' but found it to be of type '{type(var)}'")
		return False
	return True


def AddCol(msg: str, col: str) -> str:
	assert isInstance(msg, str)
	assert isInstance(col, str)

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


def PrintV(msg: str, level: int = 1) -> None:
	if level < g_verbose:
		print(AddCol(msg, "cyan"), file=sys.stderr)


def ServiceMsg(n: int) -> str:
	return  str(n) + " service" + ("s" if n > 0 else "")


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
	

def InitFiles(initdir: str) -> Sequence[str]:
	r : list[str] = []
	for f in os.listdir(initdir):
		if os.access(initdir + "/" + f, os.X_OK) and f[-1]!="~":
			r.append(f)
	r.sort()

	PrintV(f"found {ServiceMsg(len(r))} in directory '{initdir}'...")
	return r


def SysCallPrimitive(cmd: str, quiet: bool=True, checkretval: bool=False) -> tuple[list[str], int]:
	try:
		o = subprocess.getstatusoutput(cmd)

		retval = o[0]
		output = o[1].split("\n")

		assert isInstance(retval, int)
		assert isInstance(output, list)

		for i in output:
			assert isInstance(i, str)

		if not quiet:
			print("> " + cmd + " => retval=" + str(retval))
			for i in output:
				assert isInstance(i, str)
				print("  " + i)

		if checkretval and retval!=0:
			ERR(f"encountered retval!=0 in SysCallPrimitive(cmd='{cmd}', ..) {o[1]}")

		return output, retval
	except Exception as ex:
		ERR(f"encountered unexpected exception SysCallPrimitive(cmd='{cmd}', ..), exception='{ex}'")
		return "", -1


def isServiceResult(serviceresult: ServiceResult, isinit: bool=False) -> bool:
	if not isinstance(serviceresult, ServiceResult):
		return False
	if len(serviceresult.servicename) == 0:
		return False
	if not isInstance(serviceresult.output, list):
		return False
	if not isInstance(serviceresult.retval, int):
		return False
	if serviceresult.retval < -8:
		return False
	if serviceresult.retval > 1:
		return False
	if not isinit and serviceresult.retval == -1:
		return False
	if not isInstance(serviceresult.issysv, bool):
		return False
	return True


def isServiceResultsList(serviceresults: Sequence[ServiceResult], issorted : bool=True) -> bool:
	if not isInstance(serviceresults, list):
		return False		
	if issorted:
		if len(serviceresults) > 2:
			DBG(f"expected len to be 0, 1 or 2 found {len(serviceresults)}", -1)
			return False
		if len(serviceresults)==2:
			# NOTE: implicit sorting, first sysv then sysd!
			if not serviceresults[0].issysv:
				return False
			if serviceresults[1].issysv:
				return False
			if serviceresults[0].retval != serviceresults[1].retval and serviceresults[0].retval > -1 and serviceresults[1].retval > -1 :
				DBG(f"retval disagrees for service '{serviceresults[0].servicename}' and retvals {serviceresults[0].retval} / {serviceresults[1].retval}", -1)
				return False
	for i in serviceresults:
		if not isServiceResult(i):
			return False
	return True

	
def isServiceResultsDict(serviceresults: Mapping[str, Sequence[ServiceResult]]) -> bool:
	for k, v in serviceresults.items():
		if not isInstance(k, str):
			return False
		if len(k) == 0:
			return False
		if not isServiceResultsList(v):
			return False
	return True


def ServiceResultFactory(servicename: str, output: list[str], retval: int, issysv: bool, isinit: bool=False) -> ServiceResult:
	assert len(servicename) > 0
	s = ServiceResult(servicename, output, retval, issysv)
	assert isServiceResult(s, isinit)
	return s


def ServiceVStatus(results: list[ServiceResult], index: int, servicename:str, servicemode: int, isthreaded: bool, initd: str) -> None:
	assert isInstance(index, int) and index >= 0 or index == -1
	assert isInstance(servicename, str) and len(servicename) > 0
	assert isInstance(servicemode, int) and 0 <= servicemode <= 1
	assert isInstance(isthreaded, bool)

	prefix = "thread" if isthreaded else ""
	DBG(f"{prefix}[{index}], {servicename}, {servicemode}, {isthreaded}", 2)

	if servicemode == 0:
		cmd = initd + ("/" if initd[-1]!="/" else "")+ servicename + " status"
		WARN(cmd)
	elif servicemode == 1 :
		cmd = "service " + servicename + " status"
	else:
		ERR(f"unhandeled servicemode={servicemode}")

	output, retval = SysCallPrimitive(cmd)
	assert retval != 1

	DBG(f"{prefix}[{index}]: result={retval}, done")

	assert isInstance(output, list)
	assert isInstance(retval, int) and retval >= -2, f"type of r expected to be int, but is is '{type(retval)}' with value '{retval}'"

	assert index <= len(results)
	assert results[index].servicename == "N/A"

	DBG(f"service={servicename} return value={retval} to be placed in index={index} for cmd={cmd}", 1)
	
	assert retval in [0, 3]
	
	if retval == 3:
		retval = -8
	elif retval == 0:
		for i in output:
			if i.find("Active: active (exited) since") > 0:
				assert retval == 0
				retval = 1
				DBG(f"change service '{servicename}'s return value {retval} to 1 due to active but exited service ('{i}')..", 2)
				break
		
	assert retval in [-8, 0, 1], f"retval {retval} is out-of-range"
	results[index] = ServiceResultFactory(servicename, output, retval, True)


def ServiceDStatus() -> list[ServiceResult]:
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
		
	def FixServiceStr(s: str) -> str:
		if len(s) > 2 and ord(s[0]) == 9679 and s[1] == " ":
			return s[2:]
		return s

	cmd = "systemctl list-units --all --type=service --no-pager"
	output = SysCallPrimitive(cmd)
	assert isInstance(output, tuple) and len(output)==2

	o = output[0]
	r = output[1]

	assert isInstance(o, list)
	assert isInstance(r, int)

	results : list[ServiceResult] = []

	for i in o:
		assert isInstance(i, str)
		t = i.replace("\n","").strip()
		n = t.find(".service")
		if n > 0:
			servicename = FixServiceStr(t[:n])
			v = TrimWhite(t[n+8:])
			
			c = -1
			for key, val in _RESULT_STATUS.items():
				if key > -8 and v.find(val) == 0:
					c = key
					break

			if c == -1:
				WARN(f"unexpected systemctl status '{v}'")

			DBG(f"servicename={(servicename+',').ljust(48)} c={c},  v={v},  t={t}", 1)

			results.append( ServiceResultFactory(servicename, [t], c, False) )
		else:
			pass
			
	PrintV(f"found {ServiceMsg(len(results))} by calling 'systemctl'..")
	
	return results




def JoinServiceResults(results_sysv: list[ServiceResult], results_sysd: list[ServiceResult]) -> Mapping[str, list[ServiceResult]]:
	assert isServiceResultsList(results_sysv, False)
	assert isServiceResultsList(results_sysd, False)	

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
	
	assert isServiceResultsDict(r)
	return r

def FilterServiceResults(serviceresults : Mapping[str, list[ServiceResult]], filter_out : list[str], hideexited: bool, showall: bool) -> tuple[Mapping[str, list[ServiceResult]], int] :
	#toprint = (0 in [ri.retval for ri in results[k]]) if printonlyrunning else True	
	#if toprint:

	def FilterServices(s: ServiceResult, filter_out: list[str]) -> bool:
		if s.retval < 0:
			return False
		if s.retval != 0:
			if not (s.retval == 1 and not hideexited):
				return False
		for i in filter_out:
			if s.servicename.find(i) == 0:
				return False
		return True

	assert isServiceResultsDict(serviceresults)
	
	r : dict[str, list[ServiceResult]] = {}
	services_removed = 0
	
	for k, v in serviceresults.items():
		l : list[ServiceResult] = []
		for s in v:
			if showall or FilterServices(s, filter_out):
				l.append(s)
			else:
				services_removed += 1
		if len(l) > 0:
			assert k not in r
			r[k] = l
			
	assert isServiceResultsDict(r)
			
	return r, services_removed


def SortServiceResults(results: Mapping[str, list[ServiceResult]]) -> tuple[list[str], int]:
	sorted_keys : list[str] = []
	
	for k in sorted(results.keys(), key=lambda i: i.lower()):
		assert k not in sorted_keys
		sorted_keys.append(k)

	if len(sorted_keys) == 0:
		WARN("stange, found no services to print!?!")
		return [], -1

	maxlens : list[int] = [len(j) for j in sorted_keys]
	maxlens.sort()
	maxlen = maxlens[-1]
	if len(maxlens) > 1 and maxlen-maxlens[-2] > 8:
		# NOTE: just a single long line, ignore it and use then next-longest line
		maxlen = maxlens[-2]

	return sorted_keys, maxlen


def PrintServiceResults(results: Mapping[str, list[ServiceResult]]) -> None:

	def PrintServiceResultsSub(servicename: str, r: int, srv: int, maxlen: int) -> None:
			assert 0 <= srv <= 4

			s = f"[?{r}?]"
			match r:
				case 0:
					s = "+"
					col ="lgreen"
				case 1:
					s = "x"
					col = "green"
				#case 2:
				#	s = "2"
				#	col = "lyellow"
				case -2 | - 3 | -4 | -5 | -6 | -7 | -8:
					s = "-"
					col = "red"
				case _:
					WARN(f"unhandled return mode for r={r}")
					col = "yellow"
					s = str(r)
			n = len(s)
			assert n==1 or (n and r < 0)
			s = AddCol(s, col)
			s = " [" + (" " if n==1 else "") + s + " ] " 
			
			printsrv = ""
			
			if g_verbose > 0:
				printretval = ""
				if g_verbose > 1:
					v = f" 'unknown' ({r})"
					g =_RESULT_STATUS.get(r)
					if g is not None:
						v = g
					printretval = ", '" + v + "'"
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
				printsrv = " (" + printsrv + printretval + ")"	
				

			printservicename = servicename.ljust(maxlen if g_verbose > 0 else -1)
			msg = AddCol(printservicename, col)
	
			if g_verbose > 0:
				msg += AddCol(printsrv, "purple") 
		
			print(f"{s} {msg}")

	sorted_keys, maxlen = SortServiceResults(results)

	for k in sorted_keys:
		v = results[k]
		n = len(v)
		assert 1 <= n <= 2 
		
		for i in range(n):
			ri = v[i]
			
			assert k == ri.servicename
			assert (n == 1) or ((i==0 and ri.issysv) or (i==1 and not ri.issysv)), "implicit sorting in sublist, sysv then sysd"
			
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
	parser.add_argument("-a",  "--showall",     default = False,  action="store_true", help="show all services, both active and inactive, default=False\n")
	parser.add_argument("-b",  "--both",        default = False,  action="store_true", help="show both sysv and systemd services, default=False\n")
	parser.add_argument("-d",  "--debug",       default = False,  action="store_true", help="debug print default=False\n")
	parser.add_argument("-nc", "--nocolors",    default = False,  action="store_true", help="disable print with colors, default=False\n")
	parser.add_argument("-f",  "--filter",      default = False,  action="store_true", help="ignore irrelevant services in  'systemctl' mode, default=False\n")
	parser.add_argument("-x",  "--hideexited",  default = False,  action="store_true", help="hide active but exited services, default=False\n")
	parser.add_argument("-n",  "--nonthreaded", default = False,  action="store_true", help="do not use threading for speedup, default=False\n")
	parser.add_argument("-s",  "--systemctl",   default = False,  action="store_true", help="use 'systemctl' command instead of 'service', default=False\n")
	parser.add_argument("-v",  "--verbose",     default = 0,      action="count",      help="increase output verbosity, default=0\n")
	parser.add_argument("--favorite",           default = False,  action="store_true", help=f"use favorite arguments '-b -f -x', default=False\n")
	parser.add_argument("--direct",             default = False,  action="store_true", help=f"call '{initd}' directly instead of using 'service', default=False\n")
	parser.add_argument("--initdir",            default = initd,  type=str,            help=f"init dir to scan, default='{initd}'\n")
	args = parser.parse_args()
	
	if args.favorite:
		if args.verbose > 0 and (args.showall or args.debug or args.nocolors or args.nonthreaded or args.systemctl or args.direct or args.initdir != initd):
			WARN("overriding some arguments with '--favorite' switch..")
		args = parser.parse_args(["--both", "--filter", "--hideexited"])
		
	global g_verbose, g_debug_level, g_addcols
		
	g_verbose     = args.verbose
	g_debug_level = args.debug
	g_addcols     = not args.nocolors 
	
	initdir       = args.initdir
	bothmode      = args.both
	servicemode   = 2 if args.systemctl else (1 if not args.direct else 0)
	filterout : list[str] = ["user@", "getty@", "user-runtime-dir@", "systemd-fsck@", "systemd-"] if args.filter else []

	if args.showall:
		if args.hideexited:
			ERR("you can not specify both --hideexited and --showall")
	
		if args.filter:
			WARN("you specified both --filter and --showall so filtering will be deactivated")

	if args.direct and args.systemctl:
		WARN("you specified both --direct and --systemctl, using --systemctl")

	if args.both and args.systemctl:
		WARN("you specified both --both and -systemctl, using --both")

	if args.filter and not (args.systemctl or args.both):
		WARN("you specified --filter but not -systemctl or --both, filtering only has effect on systemctl services")

	if servicemode == 0:
		WARN(f"calling '{initd}' may not produce the right status for services")

	# Get sysv status..
	results_sysv : list[ServiceResult]    = []
	threads      : list[threading.Thread] = []
	
	if servicemode < 2 or bothmode:
		services = InitFiles(initdir)
		n        = len(services)
		subservicemode = 0 if args.direct else 1
		
		if n<=0:
			WARN(f"no files in init dir '{initdir}'")

		for i in range(n):
			results_sysv.append(ServiceResultFactory("N/A", [], -1, True, True))

			if args.nonthreaded:
				ServiceVStatus(                                   results_sysv, i, services[i], subservicemode, False, initd)
			else:
				x = threading.Thread(target=ServiceVStatus, args=(results_sysv, i, services[i], subservicemode, True,  initd))
				threads.append(x)
				x.start()

	assert (args.nonthreaded and len(threads)==0) or len(threads)==len(results_sysv)

	# Get systemd status..
	results_sysd : list[ServiceResult] = []
	if servicemode>=2 or bothmode:
		results_sysd = ServiceDStatus()

	# Join all threads for sysv status..
	for x in threads:
		assert isInstance(x, threading.Thread)
		x.join()

	# Join sysv and sysd results if needed..
	results = JoinServiceResults(results_sysv, results_sysd)

	# Final filtering of services..
	services_found = len(results)
	results, services_filtered = FilterServiceResults(results, filterout, args.hideexited, args.showall)

	assert services_found <=  len(results) + services_filtered
	PrintV(f"found total {ServiceMsg(services_found)}, merged {ServiceMsg(len(results))} and filtered out {services_filtered} services..")
	
	PrintServiceResults(results)


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt as _:
		ERR("interrupted by keyboard Ctld-C, aborted")
	except Exception as e:
		WARN(f"exception occured, '{e}' ({str(type(e)).replace('<class ','').replace('>','')})")
		raise e
