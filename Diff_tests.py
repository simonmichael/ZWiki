from testsupport import *
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZWiki')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite

class Tests(ZwikiTestCase):

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

