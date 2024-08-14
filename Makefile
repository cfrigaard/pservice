PYFILE=./pservice.py

test:
	$(PYFILE) -v -v -b -f -x 
			
test_some_combinations:
	@# NOTE: perhaps a generator would be better
	@# instead of this manual combination set?
	$(PYFILE) -b -n -f -x >/dev/null
	$(PYFILE) -b -n    -x >/dev/null
	$(PYFILE) -b    -f -x >/dev/null
	$(PYFILE) -b       -x >/dev/null
	$(PYFILE) -s -n -f -x >/dev/null
	$(PYFILE) -s -n    -x >/dev/null
	$(PYFILE) -s    -f -x >/dev/null
	$(PYFILE) -s       -x >/dev/null
	$(PYFILE) -b -n -f    >/dev/null
	$(PYFILE) -b -n       >/dev/null
	$(PYFILE) -b    -f    >/dev/null
	$(PYFILE) -b          >/dev/null
	$(PYFILE) -s -n -f    >/dev/null
	$(PYFILE) -s -n       >/dev/null
	$(PYFILE) -s    -f    >/dev/null
	$(PYFILE) -s          >/dev/null
	$(PYFILE) -a          >/dev/null
	$(PYFILE) -a -nc      >/dev/null
	./demo.sh             >/dev/null
	@ echo OK

lint:
	mypy --disallow-untyped-defs $(PYFILE) # --strict
	pylint --jobs 0 --disable=W0311,C0114,C0116,C0103,C0301,C0303 $(PYFILE)

edit:
	joe $(PYFILE)