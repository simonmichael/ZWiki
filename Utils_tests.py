from testsupport import *
#ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):
    def test_checkSufficientId(self):
        p, r = self.page, self.request
        self.failUnless(p.checkSufficientId(r))
        p.edits_need_username = 1
        self.failIf(p.checkSufficientId(r))
        p.edits_need_username = 0
        self.failUnless(p.checkSufficientId(r))
