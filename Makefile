install:
	pip install -r requirements.txt
	git submodule update --init
	cd mining/Pokemon-Showdown && npm install --production
	cp mining/js/* mining/Pokemon-Showdown/
	@echo "Dependencies installed. Run 'make test' to test."

test:
	nosetests --logging-clear-handlers --processes=-1

test.verbose:
	nosetests

pylint:
	pylint $(shell find . -mindepth 1 -maxdepth 1 -name "*.py" -or -type d ! -name .git ! -name tests)

clean:
	find . -name "*.py[co]" -delete
