from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

    def test_commentCount(self):
        p = self.page
        self.assertEqual(p.commentCount(),0)
        p.comment('test')
        self.assertEqual(p.commentCount(),1)
        p.comment('test')
        self.assertEqual(p.commentCount(),2)

