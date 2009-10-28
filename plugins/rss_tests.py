from Products.ZWiki.tests.testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    # def afterSetUp(self):
    #     ZwikiTestCase.afterSetUp(self)
    #     self.p.REQUEST.REMOTE_ADDR = '1'
    #     self.p.resetVotes()
    #     self.p.ensureCatalog() # tests only, nowadays zwikis have catalogs

    def test_pages_rss(self):
        p, f = self.page, self.wiki
        # boring pages are not included in feed
        self.assert_(p.isBoring())
        self.assertEqual(0, p.pages_rss().count('<item'))
        # all non-boring pages are
        p.create('NewPage')
        f.NewPage.reparent()
        self.assert_(not f.NewPage.isBoring())
        self.assertEqual(1, p.pages_rss().count('<item'))

    def test_edits_rss(self):
        p, f = self.page, self.wiki
        p.create('NewPage')
        f.NewPage.reparent()
        self.assert_(not f.NewPage.isBoring())
        self.assertEqual(1, p.edits_rss().count('<item'))

    def test_children_rss(self):
        p, f = self.page, self.wiki
        p.create('A')
        f.A.reparent()
        f.A.create('A1')
        f.A1.create('A1A')
        f.A1.create('A1B')
        self.assertEqual(1, f.A.children_rss().count('<item'))
        self.assertEqual(2, f.A1.children_rss().count('<item'))


