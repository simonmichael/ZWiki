The Zwiki unit tests. 

These have not been tested with versions other than Zope 2.7 recently.
See http://zopewiki.org/TestingZope for help with running these.
They require
- the ZopeTestCase package, installed under SOFTWARE_HOME/lib/python/Testing
- the CMF product(s) (permissions used in support.py)
- the Plone product(s) (for testCMFPlone.py)
- two fixes to CMFPlone/tests/PloneTestcase.py::

  default_user = 'testuser' #SKWM ZopeTestCase.user_name no longer exists

 and::

  #SKWM "AttributeError: 'module' object has no attribute 'Functional'"
  #class FunctionalTestCase(ZopeTestCase.Functional, PloneTestCase):
  #    '''Convenience class for functional unit testing'''

- TextIndexNG2 installation (?). Do 'python setup.py install' in
  Products/TextIndexNG2 to install some required c modules.

This test suite has mostly grown opportunistically: tests are added as
needed, eg when writing a new piece of code, when fixing a bug, or when
trying to understand some behaviour. Gradually the coverage is becoming
more complete, and the tests and infrastructure are becoming more robust.

Naming conventions: where possible, test files, classes and methods
correspond to the names of the things they test. The goal is to make it
extremely quick, easy and mechanical to jump between code and tests.  So
generally each source file has a corresponding testMODULENAME.py file, and
each method should have a test_METHODNAME test method. There are
additional test methods which don't correspond one-to-one; these do not
have _ in their names.
