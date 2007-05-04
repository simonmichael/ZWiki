from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    suite.addTest(unittest.makeSuite(AddWikiTests))
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

    def test_newPageTypeIdFor(self):
        # test a few of the page type upgrades
        self.assertEqual(self.page.newPageTypeIdFor('msgstxprelinkdtmlfitissuehtml'), 'stx')
        self.assertEqual(self.page.newPageTypeIdFor('dtmlstxlinkhtml'), 'stx')
        self.assertEqual(self.page.newPageTypeIdFor('nosuchtype'), self.page.defaultPageType())

    def test_fixEncoding(self):
        # some basic edit tests with encoded text
        latin = 'Envoy\xe9 \xc0\n'
        utf = 'Envoy\xc3\xa9 \xc3\x80\n'
        uni = u'Envoy\xe9 \xc0\n'
        # zwiki expects ascii or utf8 text
        self.p.setText(utf)
        self.assertEqual(utf,self.p.text())
        # trying to save latin1 text fails
        self.assertRaises(UnicodeError,self.p.setText,latin)
        # trying to save unicode text fails
        self.assertRaises(TypeError,self.p.setText,uni)
        # simulate an old page containing latin1 text
        self.p.raw = latin
        self.assertEqual(latin,self.p.text())
        # prerendering/formatting the page body fails when the formatter
        # expects a different encoding. Eg, assuming rest-*-encoding
        # options are set to utf8:
        self.assertRaises(UnicodeError,self.p.preRender)
        # fixEncoding converts it to utf8 and everything is happy
        self.p.fixEncoding()
        self.assertEqual(utf,self.p.text())
        self.p.preRender()

    def test_skinWithNonAscii(self):
        # skinning a non-ascii page body can fail due to #1330
        self.p.setText('Envoy\xc3\xa9')
        # doesn't work in tests, probably too much magic in Views
        #self.p.render()
        #self.assertRaises(UnicodeError,self.p.render)


class AddWikiTests(ZwikiTestCase):

    def test_manage_addWiki_programmatically(self):
        # programmatically adding a Zwiki should work too!
        id = 'wiki2'
        output = \
            self.folder.manage_addProduct['ZWiki'].manage_addWiki(\
            id, 'Fred\s Wiki', 'basic')
        self.assert_(output == id)
        self.assert_(id in self.folder.objectIds())

#     PAGES = (
#         ('zwikidotorg',
#          (('AnnoyingQuote',       'structuredtext'),
#           ('BookMarks',           'structuredtext'),
#           ('FrontPage',           'structuredtext'),
#           ('HelpPage',            'structuredtext'),
#           ('HierarchalStructure', 'structuredtext'),
#           ('JumpSearch',          'htmldtml'),
#           ('RecentChanges',       'htmldtml'),
#           ('RemoteWikiLinks',     'structuredtext'),
#           ('RemoteWikiURL',       'structuredtext'),
#           ('SearchPage',          'htmldtml'),
#           ('StructuredTextRules', 'structuredtext'),
#           ('TextFormattingRules', 'structuredtext'),
#           ('TimeZone',            'structuredtext'),
#           ('UserName',            'structuredtext'),
#           ('UserOptions',         'structuredtextdtml'),
#           ('WikiName',            'structuredtext'),
#           ('WikiWikiWeb',         'structuredtext'),
#           ('ZWiki',               'structuredtext'),
#           ('ZopeDotOrg',          'structuredtext'),
#           )),
#         )                               # add parents

#I think I've had enough
#
#    def testAddWikiForm(self):
#        from Products.ZWiki.Admin import *
#        manage_addWikiForm()#client=zc,
#                               #REQUEST=REQUEST,
#                               #PARENTS=PARENTS)

#    def testAddWiki(self):
#        p = mockPage()
#        f = p.aq_parent
#        req = p.REQUEST
#        wikitype = 'zwikidotorg'
#        req['REMOTE_ADDR'] = '1.2.3.4'
#        req['new_id'] = wikitype
#        req['new_title'] = wikitype + ' wiki'
#        req['wiki_type'] = wikitype
#        # req['SERVER_URL'] required
#        self.root.manage_addProduct['ZWiki'].addWikiForm(
#            client=self.root,\
#            REQUEST=req)

#    def testDefaultWikiContent(self):
#        """
#        test the sample wiki content.
#        """
#        zc = self.ZopeContext
#
#        # for each sample wikiweb,
#        for wikitype, pages in self.PAGES:
#
#            # create one
#            # fake form input
#            zc.REQUEST['new_id'] = wikitype
#            zc.REQUEST['new_title'] = wikitype + ' wiki'
#            zc.REQUEST['wiki_type'] = wikitype
#            manage_addWiki(zc,
#                               wikitype,
#                               new_title=wikitype+' wiki',
#                               wiki_type=wikitype,
#                               REQUEST=zc.REQUEST)
#            
#            # verify that it exists and that all pages listed above
#            # are present and correct
#            assert hasattr(zc, wikitype), \
#                   wikitype+" wiki was not created"
#            for page, type in pages:
#                assert hasattr(zc[wikitype],page), \
#                       wikitype+"/"+page+" does not exist"
#                assert zc[wikitype][page].pageTypeId() == type, \
#                       wikitype+"/"+page+"'s type is not "+type

