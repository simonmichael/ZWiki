import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class MessagesTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_messageCount(self):
        p = self.page
        self.assertEqual(p.messageCount(),0)
        p.comment('test')
        self.assertEqual(p.messageCount(),1)
        p.comment('test')
        self.assertEqual(p.messageCount(),2)

if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(MessagesTests))
        return suite
