import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
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

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(CommentsTests))
        return suite
