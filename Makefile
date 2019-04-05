all: virtualenv
	. virtualenv/bin/activate ; python3 -m kbCreator

depends: virtualenv
	@ echo -n ""

virtualenv:
	python3 -m virtualenv -p python3 virtualenv
	-make depends
