The Zwiki unit tests. These currently rely on ZopeTestCase; some older
mock classes in support.py; CMF (permissions used in support.py); and in
the case of testCMFPlone.py, PloneTestCase, Plone 2, and all it's
dependencies. They may not pass with zope versions other than 2.6.x.

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
