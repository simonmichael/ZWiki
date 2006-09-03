About the Zwiki unit tests 

XXX old, needs update:

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



# Unit tests for ZWiki. These have been through a few contortions.
# Working on simplifying them and conforming to the latest One True Way
# (running at the command line via testrunner.py). 
#
# Old notes:
#
#  how to do authentication/permissions-related testing ?
#
#  test functionality of all the different page types, with no, good &
#  bad dtml
#
#  test edit's various cases
#
#  test leading & trailing newline preservation
#
#  test initial http-like-header: preservation
#
#  test whether stx heading on first line works
#
#  test all the various kinds of links - mailto, http, wikiname,
#  remotewikilink, stx, combinations..
#
#  test handling of large cookies, empty cookies, missing cookies by
#  UserOptions, editform, standard_wiki_header...
#
#  test rendering without dtml methods and with various other versions
#  of the methods
#
#  test with other zope versions (at least product startup). Test
#  with/without ZWikiWebs; ZUnit; doctest; other ZWiki versions; other
#  related products
#
#  test zwiki_base,page_url with & without a SiteRoot
#
#  test permissions
#
#  the prerelease checklist on http://zwiki.org/ZWikiWebs
#
#  check all version nos. are correct (special prerelease test ?)
#
#  what's the best way to handle sometimes-applicable tests - like the
#  above, or testing virtual hosting only if SiteAccess is found 
#
#  tests that would catch eg the deepappend bug that broke page
#  creation from a top-level page, eg: visit both
#  TestPage/editform?page=NewPage and
#  TestPage/SubPage/editform?page=NewPage, in a basic wiki (simple
#  title) and a zwikidotorg wiki (with show_hierarchy enabled)
#  (SubPage should be a child of TestPage, add this to setup)
