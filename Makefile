all: virtualenv
	. virtualenv/bin/activate ; python3 -m docRefNetCreator

depends: virtualenv
	make upgrade_pip
	. virtualenv/bin/activate ; pip install -U -r requirements.txt

virtualenv:
	python3 -m virtualenv -p python3 virtualenv
	make depends

upgrade_pip: virtualenv
	. virtualenv/bin/activate ; pip install --upgrade pip

orange:
	. virtualenv/bin/activate ; orange-canvas
