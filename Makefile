all: virtualenv
	. virtualenv/bin/activate ; python3 -m kbCreator

depends: virtualenv
	. virtualenv/bin/activate ; pip install -r requirements.txt

virtualenv:
	python3 -m virtualenv -p python3 virtualenv
	make depends
