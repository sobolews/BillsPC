install:
	pip install -r requirements.txt
	git submodule update --init
	cd mining/Pokemon-Showdown && npm install --production
	cp mining/js/* mining/Pokemon-Showdown/
	@echo "Dependencies installed. Run 'make test' to test."

test:
	nosetests --logging-clear-handlers

test.verbose:
	nosetests

clean:
	find . -name "*.py[co]" -delete
