TESTRUNNER=/zope/bin/testrunner.py

all: test_zwiki_org test_plone_zwiki_org

test%:
	-python $(TESTRUNNER) -f test$*.py

clean:
	rm -f *~ *#
