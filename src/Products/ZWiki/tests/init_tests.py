from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    # suite.addTest(unittest.makeSuite(Tests))
    suite.addTest(unittest.makeSuite(AddWikiTests))
    return suite

class AddWikiTests(ZwikiTestCase):

    def test_addWikiFromFs(self):
        self.folder.manage_addProduct['ZWiki'].addWikiFromFs('wiki_one', \
        title='xy', wiki_type='basic', REQUEST=None)
        self.assert_('wiki_one' in self.folder.objectIds())
        self.assert_('FrontPage' in \
        self.folder.wiki_one.objectIds('ZWiki Page'))

    def test_manage_addWiki_programmatically(self):
        # programmatically adding a Zwiki should work too!
        id = 'wiki2'
        output = \
            self.folder.manage_addProduct['ZWiki'].manage_addWiki(\
            id, 'Fred\s Wiki', 'basic')
        self.assert_(output == id)
        self.assert_(id in self.folder.objectIds())
        self.assertRaises(\
            AttributeError,
            self.folder.manage_addProduct['ZWiki'].manage_addWiki,
            'anotherid', 'title', 'no-such-wiki-type')

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

