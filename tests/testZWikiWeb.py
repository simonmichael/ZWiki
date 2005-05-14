# unit tests for wiki templates

from support import *


class ZWikiWebsTests(unittest.TestCase):

    TEMPLATES = (
        ('zwikidotorg',
         (('AnnoyingQuote',       'structuredtext'),
          ('BookMarks',           'structuredtext'),
          ('FrontPage',           'structuredtext'),
          ('HelpPage',            'structuredtext'),
          ('HierarchalStructure', 'structuredtext'),
          ('JumpSearch',          'htmldtml'),
          ('RecentChanges',       'htmldtml'),
          ('RemoteWikiLinks',     'structuredtext'),
          ('RemoteWikiURL',       'structuredtext'),
          ('SearchPage',          'htmldtml'),
          ('StructuredTextRules', 'structuredtext'),
          ('TextFormattingRules', 'structuredtext'),
          ('TimeZone',            'structuredtext'),
          ('UserName',            'structuredtext'),
          ('UserOptions',         'structuredtextdtml'),
          ('WikiName',            'structuredtext'),
          ('WikiWikiWeb',         'structuredtext'),
          ('ZWiki',               'structuredtext'),
          ('ZopeDotOrg',          'structuredtext'),
          )),
        )                               # add parents

#I think I've had enough
#
#    def testAddZwikiWebForm(self):
#        from Products.ZWiki.ZWikiWeb import *
#        manage_addZWikiWebForm()#client=zc,
#                               #REQUEST=REQUEST,
#                               #PARENTS=PARENTS)

#    def testAddZwikiWeb(self):
#        p = mockPage()
#        f = p.aq_parent
#        req = p.REQUEST
#        wikitype = 'zwikidotorg'
#        req['REMOTE_ADDR'] = '1.2.3.4'
#        req['new_id'] = wikitype
#        req['new_title'] = wikitype + ' wiki'
#        req['wiki_type'] = wikitype
#        # req['SERVER_URL'] required
#        self.root.manage_addProduct['ZWiki'].ZWikiWebAddForm(
#            client=self.root,\
#            REQUEST=req)

#    def testDefaultWikiContent(self):
#        """
#        test the sample wiki content.
#        """
#        zc = self.ZopeContext
#
#        # for each sample wikiweb,
#        for wikitype, pages in self.TEMPLATES:
#
#            # create one
#            # fake form input
#            zc.REQUEST['new_id'] = wikitype
#            zc.REQUEST['new_title'] = wikitype + ' wiki'
#            zc.REQUEST['wiki_type'] = wikitype
#            manage_addZWikiWeb(zc,
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ZWikiWebsTests))
    return suite

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__ == '__main__':
    main()
