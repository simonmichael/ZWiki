import string
from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class CommentsTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_commentCount(self):
        p = self.page
        self.assertEqual(p.commentCount(),0)
        p.comment('test')
        self.assertEqual(p.commentCount(),1)
        p.comment('test')
        self.assertEqual(p.commentCount(),2)

    def test_unicodeInComments(self):
        p = self.page
        u = unicode(string.uppercase,'utf8')
        p.comment(text=u)
        self.assertEqual(p.commentCount(),1)
        self.assertEqual(p.comments()[-1].get_payload(),u)

import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CommentsTests))
    return suite
