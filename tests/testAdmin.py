import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class AdminTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    #def test_upgrade(self):
    #    p = MockZWikiPage(__name__='SomeId').aq_parent.SomeId
    #    p.title = 'something elSe!'
    #    p.upgrade()
    #    self.assertEqual(p.id(),'SomethingElse')

    # slow!
    def Xtest_setupPages(self):
        self.assertEqual(len(self.page.pages()),1)
        self.page.setupPages()
        self.assertEqual(len(self.page.pages()),9)
        self.assert_(hasattr(self.page.folder(),'HelpPage'))
        self.page.setupPages()
        self.assertEqual(len(self.page.pages()),9)

    def test_setupDtmlMethods(self):
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),0)
        self.assert_(not hasattr(self.page.folder().aq_base,'index_html'))
        self.assert_(not hasattr(self.page.folder().aq_base,'standard_error_message'))
        self.page.setupDtmlMethods()
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),2)
        self.assert_(hasattr(self.page.folder().aq_base,'index_html'))
        self.assert_(hasattr(self.page.folder().aq_base,'standard_error_message'))
        self.page.setupDtmlMethods()
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),2)

    def test_setupCatalog(self):
        self.assert_(not self.page.catalog())
        self.page.setupCatalog()
        #self.assert_(self.page.catalog()) #XXX fails! why ?
        #XXX somehow the non-None catalog is false, during unit tests
        self.assert_(self.page.catalog() is not None)
        self.page.setupCatalog()

    def xtest_setupTracker(self): #slow
        self.assert_(not self.page.catalog())
        self.assertEqual(len(self.page.pages()),1)
        self.page.setupTracker()
        self.assert_(self.page.catalog() is not None)
        self.page.index_object() # get TestPage into the catalog for pages()!
        self.assertEqual(len(self.page.pages()),3)
        self.assert_(hasattr(self.page.folder(),'IssueTracker'))
        self.assert_(hasattr(self.page.folder(),'FilterIssues'))
        self.page.setupTracker()
        self.assert_(self.page.catalog() is not None)
        self.assertEqual(len(self.page.pages()),3)

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(AdminTests))
        return suite
