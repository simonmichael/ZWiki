from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    #def test_upgrade(self):
    #    p = mockPage(__name__='SomeId').aq_parent.SomeId
    #    p.title = 'something elSe!'
    #    p.upgrade()
    #    self.assertEqual(p.id(),'SomethingElse')

    # slow!
    def Xtest_setupPages(self):
        self.assertEqual(len(self.page.pages()),1)
        self.page.setupPages()
        self.assertEqual(len(self.page.pages()),9)
        self.assert_(safe_hasattr(self.page.folder(),'HelpPage'))
        self.page.setupPages()
        self.assertEqual(len(self.page.pages()),9)

    def test_setupDtmlMethods(self):
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),0)
        self.assert_(not safe_hasattr(self.page.folder().aq_base,'index_html'))
        self.assert_(not safe_hasattr(self.page.folder().aq_base,'standard_error_message'))
        self.page.setupDtmlMethods()
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),3)
        self.assert_(safe_hasattr(self.page.folder().aq_base,'index_html'))
        self.assert_(safe_hasattr(self.page.folder().aq_base,'standard_error_message'))
        self.page.setupDtmlMethods()
        self.assertEqual(len(self.page.folder().objectIds(spec='DTML Method')),3)

    def test_setupCatalog(self):
        self.assert_(not self.page.catalog())
        self.page.setupCatalog()
        #self.assert_(self.page.catalog()) #XXX fails! why ?
        #XXX somehow the non-None catalog is false, during unit tests
        self.assert_(self.page.catalog() is not None)
        self.page.setupCatalog()

    def test_setupCatalog_upgrades_TextIndex(self):
        self.page.setupPages()
        self.page.setupCatalog()
        catalog = self.page.catalog()
        # delete what we have
        catalog.delIndex('SearchableText')
        catalog.delIndex('Title')
        # add "old" TextIndex class indexes
        PluginIndexes = catalog.manage_addProduct['PluginIndexes']
        PluginIndexes.manage_addTextIndex('Title')
        PluginIndexes.manage_addTextIndex('SearchableText')
        # this worked?
        self.assert_(catalog._catalog.getIndex('Title').meta_type == 'TextIndex')
        # now upgrade those indexes within setupCatalog
        self.page.setupCatalog()
        self.assert_(catalog._catalog.getIndex('Title').meta_type == 'ZCTextIndex')
        self.assert_(catalog._catalog.getIndex('SearchableText').meta_type == 'ZCTextIndex')
        # filled:
        self.assertEqual(catalog._catalog.getIndex('SearchableText').indexSize(), 4)

    def xtest_setupTracker(self): #slow
        self.assert_(not self.page.catalog())
        self.assertEqual(len(self.page.pages()),1)
        self.page.setupTracker()
        self.assert_(self.page.catalog() is not None)
        self.page.index_object() # get TestPage into the catalog for pages()!
        self.assertEqual(len(self.page.pages()),3)
        self.assert_(safe_hasattr(self.page.folder(),'IssueTracker'))
        self.assert_(safe_hasattr(self.page.folder(),'FilterIssues'))
        self.page.setupTracker()
        self.assert_(self.page.catalog() is not None)
        self.assertEqual(len(self.page.pages()),3)

    def test_newPageTypeIdFor(self):
        # test a few of the page type upgrades
        self.assertEqual(self.page.newPageTypeIdFor('msgstxprelinkdtmlfitissuehtml'), 'stx')
        self.assertEqual(self.page.newPageTypeIdFor('dtmlstxlinkhtml'), 'stx')
        self.assertEqual(self.page.newPageTypeIdFor('nosuchtype'), self.page.defaultPageType())

    def test_fixEncoding(self):
        # some basic tests with encoded text
        uni = u'Envoy\xe9 \xc0\n'
        utf = 'Envoy\xc3\xa9 \xc3\x80\n'
        latin = 'Envoy\xe9 \xc0\n'
        # most zwiki text handling methods now expect and return unicode
        self.p.setText(uni)
        self.assertEqual(uni,self.p.text())
        # setText/cleanupText will accept plain ascii or utf8, also
        self.p.setText(utf)
        self.assertEqual(uni,self.p.text())
        # trying to save latin1 text fails
        self.assertRaises(UnicodeError,self.p.setText,latin)
        # simulate prerendering/formatting an old page containing latin1
        # This fails when the formatter expects a different encoding. Eg,
        # assuming rest-*-encoding options are set to utf8:
        self.p.raw = latin
        self.assertRaises(UnicodeError,self.p.preRender)
        # fixEncoding converts it to unicode and everything is happy
        # but we must specify the encoding if it's different from the wiki's default
        self.p.fixEncoding(enc='latin1')
        self.assertEqual(uni,self.p.text())
        self.p.preRender()
        # should also fix an old page's utf8-encoded parents property
        self.p.parents = ['\xc3\x89']
        self.p.fixEncoding()
        self.assertEqual([u'\xc9'],self.p.getParents())

    def test_skinWithNonAscii(self):
        # skinning a non-ascii page body can fail due to #1330
        self.p.setText('Envoy\xc3\xa9')
        # doesn't work in tests, probably too much magic in Views
        #self.p.render()
        #self.assertRaises(UnicodeError,self.p.render)

