"""This is a a functional doctest test. It uses ZopeTestCase and doctest
syntax. In the test itself, we use zope.testbrowser to test end-to-end
functionality, including the UI.

One important thing to note: zope.testbrowser is not JavaScript aware! For
that, you need a real browser. Look at zope.testbrowser.real and Selenium
if you require "real" browser testing.
"""

import unittest
import doctest


from Testing import ZopeTestCase
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

try:
    from zope import traversing, component, interface
except ImportError:
    print '--------------------------------------------'
    print 'Functional tests will only run in Zope 2.10+'
    print '--------------------------------------------'
    raise
from zope.traversing.adapters import DefaultTraversable
from zope.traversing.interfaces import ITraversable
from zope.component import provideAdapter
from zope import interface
from zope.interface import implements

class TestZWikiFunctional(ZopeTestCase.FunctionalTestCase):
    """
    Testing browser paths through ZWiki.
    """
    implements(ITraversable)

    def beforeSetUp(self):
        super(ZopeTestCase.FunctionalTestCase, self).beforeSetUp()
        component.provideAdapter( \
                    traversing.adapters.DefaultTraversable, (interface.Interface,),ITraversable)

    def testSomething(self):
        # This is here, because otherwise beforeSetUp wouldn't be run
        pass

def test_suite():
    suite = unittest.makeSuite(TestZWikiFunctional)
    suite.addTest(ZopeTestCase.FunctionalDocFileSuite(
            'functional.txt', package='Products.ZWiki.tests',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE | 
                        doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS))
    return suite

if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
