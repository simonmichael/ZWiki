import os, sys
if __name__ == '__main__': execfile(os.path.join(sys.path[0], 'framework.py'))
from Testing import ZopeTestCase
from support import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

class DiffTests(ZopeTestCase.ZopeTestCase):
    def afterSetUp(self):
        zwikiAfterSetUp(self)

    def test_textDiff(self):
        p = self.page
        self.assertEqual(p.textDiff(a='1',
                                    b='1\n2'),
                         '''
++added:
2
''')
        self.assertEqual(p.textDiff(a='1\n2',
                                    b='2'),
                         '''
--removed:
-1
''')
        self.assertEqual(p.textDiff(a='1',
                                    b='12'),
                         '''
??changed:
-1
12
''')

    def test_htmlDiff(self):
        p = self.page
        self.assertEqual(p.htmlDiff(a='1',
                                    b='1\n2'),
                         '''
<b>added:</b><span style="color:green">
2</span>
''')
        self.assertEqual(p.htmlDiff(a='1\n2',
                                    b='2'),
                         '''
<b>removed:</b><span style="color:red;text-decoration:line-through">
-1</span>
''')
        self.assertEqual(p.htmlDiff(a='1',
                                    b='12'),
                         '''
<b>changed:</b><span style="color:red;text-decoration:line-through">
-1</span><span style="color:green">
12</span>
''')


if __name__ == '__main__':
    framework(descriptions=1, verbosity=2)
else:
    import unittest
    def test_suite():
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(DiffTests))
        return suite
