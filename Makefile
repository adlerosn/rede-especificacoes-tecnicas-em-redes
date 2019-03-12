all: virtualenv
	. virtualenv/bin/activate ; python3 -m kbCreator

depends:
	. virtualenv/bin/activate ; pip install -r requirements.txt
	. virtualenv/bin/activate ; spacy download en
	. virtualenv/bin/activate ; spacy download en_core_web_sm
	. virtualenv/bin/activate ; spacy download en_core_web_md
	. virtualenv/bin/activate ; spacy download en_core_web_lg
	. virtualenv/bin/activate ; spacy download en_vectors_web_lg

virtualenv:
	python3 -m virtualenv -p python3 virtualenv
	make depends
	

