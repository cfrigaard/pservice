#!/usr/bin/env python3

# NOTE a parallel service shell
#   History:
#     version 0.0: initial
#     version 0.1: removed external dependencies to local developer files
#     version 0.2: cleanup, published
#     version 0.3: cleaned up keyboard Ctrl-C handling

import os
import sys
import subprocess
import threading
import argparse

def ERR(msg):
	print(f"ERROR: {msg}", file=sys.stderr)
	exit(-1)

def WARN(msg):
	print(f"WARN: {msg}", file=sys.stderr)

def InitFiles(initdir):
	files = os.listdir(initdir)
	r = []
	for f in files:
		if os.access(initdir + "/" + f, os.X_OK) and f[-1]!="~":
			r.append(f)
	return sorted(r)

def main():

	def AddCol(msg, addcols, col):
		#BLUE     ="\033[0;34m"
		#LBLUE    ="\033[1;34m"
		RED      ="\033[0;31m"
		LRED     ="\033[1;31m"
		GREEN    ="\033[0;32m"
		LGREEN   ="\033[1;32m"
		YELLOW   ="\033[0;33m"
		LYELLOW  ="\033[1;33m"
		#PURPLE   ="\033[0;35m"
		#LPURPLE  ="\033[1;35m"
		CYAN     ="\033[0;36m"
		#LCYAN    ="\033[1;36m"
		NC       ="\033[0m"

		if addcols:
			if col=='red':
				msg = RED + msg
			elif col=='lred':
				msg = LRED  + msg
			elif col=='green':
				msg = GREEN + msg
			elif col=='lgreen':
				msg = LGREEN + msg
			elif col=='yellow':
				msg = YELLOW + msg
			elif col=='lyellow':
				msg = LYELLOW + msg
			elif col=='cyan':
				msg = CYAN + msg
			else:
				raise ValueError(f"color '{col}' not defined")
			msg += NC

		return msg

	def ServiceStatus(index, servicename, initdir, servicemode, debug, isthreaded, filter_out=None):

		def SysCallPrimitive(cmd, quiet=False, checkretval=False):
			try:
				o = subprocess.getstatusoutput(cmd)

				#process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				#o, _ = process.communicate()
				#if o[-1:] == b'\n':
				#	o = o[:-1]
				#retval = process.returncode #o[0]
				#output = str(o[1]).split("\n")

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
				
		def ParseSystemCtl(output_r, filter_out):
			def TrimWhite(s):
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
				
			def FilterOutIrrelevantServices(s, filter_out):
				for i in filter_out:
					if s.find(i)==0:
						return False
				return True
					
			assert isinstance(output_r, tuple) and len(output_r)==2
			
			o = output_r[0]
			r = output_r[1]
			
			assert isinstance(o, list)
			assert isinstance(r, int)
			
			files = []	
			results = {}	
			k = 0	
							
			for i in o:
				assert isinstance(i, str)
				t = i.replace("\n","").strip()
				n = t.find(".service")
				if n>0:
					s = t[:n]
					v = TrimWhite(t[n+8:])
					
					c = -1
					#if v.find("loaded    active   exited")==0:
					#	c = 3
					#elif v.find("loaded    inactive   exited")==0:
					#	c = 3
					#elif v.find("loaded    active   running")==0:
					#	c = 0
					#elif v.find("loaded    inactive dead")==0:
					#	c = 3
					#elif v.find("not-found inactive dead")==0:
					#	c = -2
					#elif v.find("masked    inactive dead")==0:
					#	c = -2
					#else:
					#	WARN(f"unexpected systemctl status '{v}'")

					if v.find("loaded active exited")==0:
						c = 1 # change to 0 if active but exited services should be marked as running
					elif v.find("loaded inactive exited")==0:
						c = 3
					elif v.find("loaded active running")==0:
						c = 0
					elif v.find("loaded inactive dead")==0:
						c = 3
					elif v.find("not-found inactive dead")==0:
						c = -2
					elif v.find("masked inactive dead")==0:
						c = -2
					elif v.find("loaded failed")==0:
						c = -2
					elif v.find("not-found failed")==0:
						c = -2
					else:
						WARN(f"unexpected systemctl status '{v}'")
					
					if debug:
						print(f"k={k}, c={c}, v={v}")
					
					if c>=0:
						if FilterOutIrrelevantServices(s, filter_out):	
							files.append(s)
							results[k] = ([s], c)
							k += 1
				else:
					pass
					#WARN(i)
					
			#print(results)
			return files, results
			
		assert isinstance(index, int) and index>=0
		assert isinstance(servicename, str) and len(servicename)>0
		assert isinstance(initdir, str) and len(initdir)>0
		assert isinstance(servicemode, int) and servicemode>=0 and servicemode<=2
		assert isinstance(debug, bool)
		assert isinstance(isthreaded, bool)

		prefix = "thread" if isthreaded else ""

		if debug:
			print(f"{prefix}[{index}]: {initdir}/{servicename} started..")

		if servicemode==0:
			cmd = "/etc/init.d/" + servicename + " status"
		elif servicemode==1:
			cmd = "service " + servicename + " status"
		elif servicemode==2:
			cmd = "systemctl list-units --all --type=service --no-pager"
			return ParseSystemCtl(SysCallPrimitive(cmd, quiet=not debug), filter_out)
		else:
			ERR("funhandeled servicemode={servicemode}")

		output, r = SysCallPrimitive(cmd, quiet=not debug)

		if debug:
			print(f"{prefix}[{index}]: result={r}, done")

		assert isinstance(output, list)
		assert isinstance(r, int) and r>=-2, f"type of r expected to be int, but is is '{type(r)}' with value '{r}'"

		assert index <= len(results)
		assert results[index]=="N/A"

		results[index]=(output, r)

	initd = "/etc/init.d"
	parser = argparse.ArgumentParser()
	parser.add_argument("-v",          		default = 0,      action="count",      help="increase output verbosity, default=0\n")
	parser.add_argument("-c",          		default = False,  action="store_true", help="add colors, default=False\n")
	parser.add_argument("-r",          		default = False,  action="store_true", help="only show running services, default=False\n")
	parser.add_argument("-i", "--initd",   	default = False,  action="store_true", help=f"call '{initd}' directly instead of using 'service'/'systemctl', default=False\n")
	parser.add_argument("-s", "--systemctl",default = False,  action="store_true", help="use 'systemctl' command instead of'service' directly, default=False\n")	
	parser.add_argument("-f", "--filter",	default = False,  action="store_true", help="ignore irrelevant services in  'systemctl' mode, default=False\n")	
	parser.add_argument("-nonthreaded",		default = False,  action="store_true", help="do not use threading for speedup, default=False\n")
	parser.add_argument("-debug",      		default = False,  action="store_true", help="debug print default=False\n")
	parser.add_argument("-initdir",    		default = initd,  type=str,            help=f"init dir to scan, default='{initd}'\n")
	args = parser.parse_args()

	initdir= args.initdir
	files  = InitFiles(initdir)
	n      = len(files)
	verbose= args.v
	debug  = args.debug
	addcols= args.c
	servicemode = 2 if args.systemctl else (1 if not args.initd else 0)
	nonthread   = args.nonthreaded

	if n<=0:
		WARN(f"no files in init dir '{initdir}'")

	if args.initd and args.systemctl:
		WARN("you specified both -s and -systemctl, using -systemctl") 
	
	if servicemode==0:
		WARN(f"calling '{initd}' may not produce the right status for services")
		
	if verbose:
		WARN("vebose flag still unused in code")

	results = {}
	threads = {}

	if servicemode==2:
		nonthread = True
		f = ["user@", "getty@", "user-runtime-dir@", "systemd-fsck@", "systemd-"] if args.filter else []
		files, results = ServiceStatus(0, "N/A", initdir, servicemode, debug, False, f)
		n = len(results)
	else:
		for i in range(n):
			results[i]="N/A"
			if nonthread:
				ServiceStatus(i, files[i], initdir, servicemode, debug, False)
			else:
				x = threading.Thread(target=ServiceStatus, args=(i, files[i], initdir, servicemode, debug, True))
				x.start()
				threads[i]=x

	assert nonthread or len(threads)==n
	assert len(results)==n

	for i in range(n):
		if not nonthread:
			x = threads[i]
			assert isinstance(x, threading.Thread)
			x.join()

		ri = results[i]

		assert isinstance(ri, tuple)
		assert len(ri)==2
		assert isinstance(ri[0], list)
		assert isinstance(ri[1], int)

		output = ri[0]
		r      = ri[1]
		
		assert isinstance(output, list)
		assert isinstance(r, int)

		s = f"[?{r}?]"
		if r==0:
			s = AddCol("+", addcols, "lgreen")
		elif r==1:
			s = AddCol("*", addcols, "green")
		elif r==2:
			s = AddCol("2", addcols, "lyellow")
		elif r==3:
			s = AddCol("-", addcols, "lred")
		s = f"[ {s} ]"

		msg = AddCol(files[i], addcols, "green" if r==0 else "red")
		if not args.r or r==0:
			print(f" {s}  {msg}")

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt as _:
		ERR("interrupted by keyboard Ctld-C, aborted")
	except Exception as e:
		ERR(f"exception occured {e} ({type(e)})")
