from Products.ZWiki.testsupport import *
from types import DictionaryType
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    def afterSetUp(self):
        ZwikiTestCase.afterSetUp(self)
        self.p.REQUEST.REMOTE_ADDR = '1'
        self.p.resetVotes()
        self.p.ensureCatalog() # tests only, nowadays zwikis have catalogs

    def test_rating(self):
        p = self.p
        self.assert_(p.rating() == 1)
        p.vote(2)
        self.assert_(p.rating() == 2)
        self.p.REQUEST.cookies['zwiki_username'] = 'someoneelse'
        p.vote(0)
        self.assert_(p.rating() == 1)

    def test_vote(self): # and voteCount
        p = self.p
        self.assert_(p.voteCount() == 0)
        p.vote(1)
        self.assert_(p.voteCount() == 1)
        p.vote(1)
        self.assert_(p.voteCount() == 1)
        self.p.REQUEST.cookies['zwiki_username'] = 'someoneelse'
        p.vote(1)
        self.assert_(p.voteCount() == 2)

    def test_ensureVotesIsBtree(self):
        p = self.p
        p._votes = {'someoneelse':3} # fakeing an old voting module
        p.ensureVotesIsBtree() # now "upgrading"
        self.failIf(isinstance(p._votes, DictionaryType), \
            'Not been converted to Btree!')
        self.assert_(p.voteCount() == 1)
        self.assertEqual(p._votes['someoneelse'], 3)
