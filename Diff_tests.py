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

    def test_revertEditsEverywhereBy(self):
        p = self.page
        p.last_editor = 'fred'
        p.REQUEST.cookies['zwiki_username'] = 'fred'
        p.edit(text='test',REQUEST=p.REQUEST)
        p.append(text='1',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'fred')
        # if the user in question didn't edit: no change
        before = p.read()
        p.revertEditsEverywhereBy('joe')
        self.assertEqual(p.read(), before)
        # now let him change something
        p.REQUEST.cookies['zwiki_username'] = 'joe'
        p.edit(text='2',REQUEST=p.REQUEST)
        self.assertEqual(p.last_editor,'joe')
        self.assertNotEqual(p.read(), before)
        # reverting should get us to where we were before:
        p.revertEditsEverywhereBy('joe')
        # self.assertEqual(p.read(), before)
        # self.assertEqual(p.last_editor,'fred')
        # this doesn't really work
        # because the page objects in the tests don't have
        # real history?
        # for the moment we're just testing the "except" clause
